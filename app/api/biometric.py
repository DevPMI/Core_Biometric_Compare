"""
Biometric API Routes
=====================
Endpoint untuk registrasi, perbandingan, dan penghapusan data biometrik.

Routes:
    POST   /api/v1/biometric/compare    - Membandingkan gambar input dengan database
    POST   /api/v1/biometric/register   - Mendaftarkan data biometrik baru
    DELETE /api/v1/biometric/<id>       - Menghapus data biometrik berdasarkan ID
    GET    /api/v1/biometric/           - Mendapatkan daftar semua data biometrik
    GET    /api/v1/biometric/<id>       - Mendapatkan detail data biometrik
"""

import os
import uuid
import logging
import cv2
import numpy as np
from flask import Blueprint, request, current_app
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.biometric import BiometricData
from app.services.face_service import (
    extract_face_embedding,
    compare_face_embeddings,
    serialize_embedding,
)
from app.services.palm_service import (
    extract_palm_features,
    compare_palm_features,
    serialize_descriptors,
)
from app.utils.responses import (
    success_response,
    error_response,
    not_found_response,
    created_response,
)
from app.utils.auth import require_api_key

logger = logging.getLogger(__name__)

bp = Blueprint("biometric", __name__, url_prefix="/api/v1/biometric")

# ──────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────

ALLOWED_TYPES = {"face", "palm"}


def _allowed_file(filename: str) -> bool:
    """Memeriksa apakah ekstensi file diperbolehkan."""
    allowed = current_app.config.get(
        "ALLOWED_EXTENSIONS", {"png", "jpg", "jpeg", "bmp", "tiff"}
    )
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def _resize_image(img: np.ndarray, max_dim: int = 640) -> np.ndarray:
    """Resize gambar agar sisi terpanjang maksimal max_dim pixel untuk kecepatan."""
    h, w = img.shape[:2]
    if w > max_dim or h > max_dim:
        ratio = min(max_dim / w, max_dim / h)
        new_w, new_h = int(w * ratio), int(h * ratio)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return img


def _save_uploaded_file(file, biometric_type: str) -> str | None:
    """
    Menyimpan file yang diupload ke folder uploads/{biometric_type}.

    Returns:
        str: Path absolut ke file yang disimpan, atau None jika gagal.
    """
    if not file or file.filename == "":
        logger.warning("Upload rejected: No file or empty filename")
        return None

    if not _allowed_file(file.filename):
        logger.warning("Upload rejected: File extension not allowed for '%s'", file.filename)
        return None

    # Generate nama file unik untuk menghindari konflik
    ext = file.filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    safe_name = secure_filename(unique_name)

    # Simpan di subdirectory berdasarkan tipe (face/palm)
    upload_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], biometric_type)
    os.makedirs(upload_folder, exist_ok=True)
    
    filepath = os.path.join(upload_folder, safe_name)
    
    # Baca dan resize gambar sebelum disimpan untuk menghemat disk & mempercepat proses
    try:
        file_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is not None:
            img = _resize_image(img, max_dim=640)
            cv2.imwrite(filepath, img)
        else:
            # Jika gagal decode dengan cv2, simpan as is
            file.seek(0)
            file.save(filepath)
    except Exception as e:
        logger.warning("Gagal resize saat save: %s", str(e))
        file.seek(0)
        file.save(filepath)

    logger.info("File saved to %s", filepath)

    return filepath





def _extract_features(image_data: str | np.ndarray, biometric_type: str):
    """
    Mengekstrak fitur biometrik sesuai tipe.

    Args:
        image_data: Path file (str) atau Image array (np.ndarray)
    
    Returns:
        Embedding/deskriptor, atau None jika gagal.
    """
    if biometric_type == "face":
        return extract_face_embedding(image_data)
    elif biometric_type == "palm":
        return extract_palm_features(image_data)
    return None


def _serialize_features(features, biometric_type: str) -> str:
    """Serialisasi fitur biometrik ke JSON string."""
    if biometric_type == "face":
        return serialize_embedding(features)
    elif biometric_type == "palm":
        return serialize_descriptors(features)
    return ""


def _compare_features(features, stored_embedding: str, biometric_type: str):
    """
    Membandingkan fitur input dengan data tersimpan.

    Returns:
        tuple: (is_match, score)
    """
    if biometric_type == "face":
        return compare_face_embeddings(features, stored_embedding)
    elif biometric_type == "palm":
        return compare_palm_features(features, stored_embedding)
    return False, 0.0


def _find_existing_match(input_features, biometric_type: str):
    """
    Mencari kecocokan data biometrik di database.

    Returns:
        tuple: (best_match_record, best_score) atau (None, 0.0)
    """
    # Ambil semua data biometrik sesuai tipe dari database
    stored_data = BiometricData.query.filter_by(
        biometric_type=biometric_type
    ).all()

    if not stored_data:
        return None, 0.0

    # Bandingkan dengan setiap data yang tersimpan
    best_match = None
    best_score = float("inf") if biometric_type == "face" else 0.0

    for record in stored_data:
        is_match, score = _compare_features(
            input_features, record.embedding, biometric_type
        )
        if is_match:
            if biometric_type == "face":
                # Face: skor lebih rendah = lebih cocok (cosine distance)
                if score < best_score:
                    best_score = score
                    best_match = record
            else:
                # Palm: skor lebih tinggi = lebih cocok (match ratio)
                if score > best_score:
                    best_score = score
                    best_match = record
    
    return best_match, best_score


@bp.route("/compare", methods=["POST"])
@require_api_key
def compare_biometric():
    """
    Membandingkan gambar biometrik dengan semua data di database.

    Request:
        - file: File gambar (form-data)
        - type: Tipe biometrik - 'face' atau 'palm' (form-data)

    Response:
        - 200: Data ditemukan → { sukses, pesan, data: { id, tipe_biometrik, skor } }
        - 404: Data tidak ditemukan
        - 400: Request tidak valid
    """
    # Validasi tipe biometrik
    biometric_type = request.form.get("type", "").lower()
    if biometric_type not in ALLOWED_TYPES:
        return error_response(
            message=f"Tipe biometrik tidak valid. Gunakan salah satu: {', '.join(ALLOWED_TYPES)}"
        )

    # Validasi file
    if "file" not in request.files:
        return error_response(message="File gambar tidak ditemukan dalam request")

    file = request.files["file"]
    if file.filename == "":
        return error_response(message="Nama file kosong")

    try:
        # Proses file di memori tanpa menyimpan ke disk
        file_bytes = np.frombuffer(file.read(), np.uint8)
        
        # Decode gambar menggunakan OpenCV
        # cv2.IMREAD_COLOR cocok untuk face (DeepFace bisa handle BGR)
        # cv2.IMREAD_GRAYSCALE bisa untuk palm, tapi service palm sudah handle konversi jika dikasih BGR
        # Jadi kita pakai COLOR agar aman untuk keduanya (Palm service akan convert ke gray jika perlu)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if img is None:
             return error_response(
                message="File tidak valid atau format gambar tidak didukung."
            )

        # Resize gambar untuk mempercepat proses deteksi wajah di CPU
        img = _resize_image(img, max_dim=640)

        # Ekstrak fitur dari gambar (numpy array)
        input_features = _extract_features(img, biometric_type)
        
        if input_features is None:
            return error_response(
                message=f"Gagal mengekstrak fitur dari gambar. "
                        f"Pastikan gambar berisi {'wajah' if biometric_type == 'face' else 'pola vena telapak tangan'} yang jelas."
            )

        # Cari kecocokan di database
        best_match, best_score = _find_existing_match(input_features, biometric_type)

        if best_match is not None:
            return success_response(
                message="Data biometrik ditemukan",
                data={
                    "id": best_match.id,
                    "biometric_type": best_match.biometric_type,
                    "match_score": round(best_score, 4),
                    "created_at": best_match.created_at.isoformat(),
                }
            )

        return not_found_response(message="Data tidak ditemukan")

    except Exception as e:
        logger.error("Error saat membandingkan biometrik: %s", str(e))
        return error_response(
            message="Terjadi kesalahan server saat memproses perbandingan",
            status_code=500
        )


@bp.route("/register", methods=["POST"])
@require_api_key
def register_biometric():
    """
    Mendaftarkan data biometrik baru ke database.

    Request:
        - file: File gambar (form-data)
        - type: Tipe biometrik - 'face' atau 'palm' (form-data)

    Response:
        - 201: Berhasil didaftarkan → { sukses, pesan, data: { id, tipe_biometrik } }
        - 400: Request tidak valid
        - 409: Data biometrik sudah terdaftar
    """
    # Validasi tipe biometrik
    biometric_type = request.form.get("type", "").lower()
    if biometric_type not in ALLOWED_TYPES:
        return error_response(
            message=f"Tipe biometrik tidak valid. Gunakan salah satu: {', '.join(ALLOWED_TYPES)}"
        )

    # Validasi file
    if "file" not in request.files:
        return error_response(message="File gambar tidak ditemukan dalam request")

    file = request.files["file"]
    filepath = _save_uploaded_file(file, biometric_type)
    if filepath is None:
        return error_response(
            message="File tidak valid. Gunakan format: PNG, JPG, JPEG, BMP, atau TIFF"
        )

    try:
        # Ekstrak fitur dari gambar
        features = _extract_features(filepath, biometric_type)
        if features is None:
            # Hapus file jika gagal
            if os.path.exists(filepath):
                os.remove(filepath)
            return error_response(
                message=f"Gagal mengekstrak fitur dari gambar. "
                        f"Pastikan gambar berisi {'wajah' if biometric_type == 'face' else 'pola vena telapak tangan'} yang jelas."
            )

        # Cek apakah data sudah ada sebelumnya
        existing_match, existing_score = _find_existing_match(features, biometric_type)
        
        if existing_match is not None:
             # Hapus file baru karena data sudah ada
            if os.path.exists(filepath):
                os.remove(filepath)
            
            return error_response(
                message=f"Data biometrik sudah terdaftar dengan ID {existing_match.id}",
                status_code=409,  # Conflict
                errors={
                    "existing_id": existing_match.id,
                    "score": round(existing_score, 4)
                }
            )

        # Serialisasi fitur untuk disimpan di database
        serialized = _serialize_features(features, biometric_type)

        # Generate Custom ID (e.g., FACE-A1B2C3D4)
        custom_id = f"{biometric_type.upper()}-{uuid.uuid4().hex[:10].upper()}"

        # Simpan ke database
        new_record = BiometricData(
            id=custom_id,
            biometric_type=biometric_type,
            image_path=filepath,
            embedding=serialized,
        )
        db.session.add(new_record)
        db.session.commit()

        logger.info(
            "Data biometrik baru terdaftar: ID=%s, tipe=%s",
            new_record.id, biometric_type
        )

        return created_response(
            message="Data biometrik berhasil didaftarkan",
            data=new_record.to_dict()
        )

    except Exception as e:
        db.session.rollback()
        logger.error("Error saat mendaftarkan biometrik: %s", str(e))
        # Hapus file jika terjadi error
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
        return error_response(
            message="Terjadi kesalahan server saat menyimpan data",
            status_code=500
        )


@bp.route("/<string:biometric_id>", methods=["DELETE"])
@require_api_key
def delete_biometric(biometric_id: str):
    """
    Menghapus data biometrik berdasarkan ID.

    Args:
        biometric_id: ID data biometrik yang akan dihapus.

    Response:
        - 200: Berhasil dihapus
        - 404: Data tidak ditemukan
    """
    try:
        record = BiometricData.query.get(biometric_id)
        if record is None:
            return not_found_response(
                message=f"Data biometrik dengan ID {biometric_id} tidak ditemukan"
            )

        # Hapus file gambar referensi jika masih ada
        if record.image_path and os.path.exists(record.image_path):
            try:
                os.remove(record.image_path)
                logger.info("File gambar dihapus: %s", record.image_path)
            except OSError as e:
                logger.warning("Gagal menghapus file gambar: %s", str(e))

        # Hapus record dari database
        db.session.delete(record)
        db.session.commit()

        logger.info("Data biometrik dihapus: ID=%s", biometric_id)

        return success_response(
            message=f"Data biometrik dengan ID {biometric_id} berhasil dihapus"
        )

    except Exception as e:
        db.session.rollback()
        logger.error("Error saat menghapus biometrik: %s", str(e))
        return error_response(
            message="Terjadi kesalahan server saat menghapus data",
            status_code=500
        )


@bp.route("/", methods=["GET"])
@require_api_key
def list_biometric():
    """
    Mendapatkan daftar semua data biometrik dengan paginasi.

    Query Params:
        - type: Filter berdasarkan tipe ('face' atau 'palm') (opsional)
        - page: Nomor halaman (default: 1)
        - limit / per_page: Jumlah data per halaman (default: 10)

    Response:
        - 200: Daftar data biometrik dengan meta informasi paginasi
    """
    biometric_type = request.args.get("type", "").lower()
    page = request.args.get("page", 1, type=int)
    # Gunakan 'limit' atau 'per_page', default ke 10
    limit = request.args.get("limit", request.args.get("per_page", 10, type=int), type=int)

    query = BiometricData.query

    if biometric_type in ALLOWED_TYPES:
        query = query.filter_by(biometric_type=biometric_type)

    # Lakukan paginasi
    paginated_data = query.order_by(BiometricData.created_at.desc()).paginate(
        page=page, per_page=limit, error_out=False
    )

    records = paginated_data.items

    meta = {
        "current_page": paginated_data.page,
        "items_per_page": paginated_data.per_page,
        "total_pages": paginated_data.pages,
        "total_items": paginated_data.total,
        "has_next": paginated_data.has_next,
        "has_prev": paginated_data.has_prev
    }

    return success_response(
        message=f"Menampilkan data halaman {paginated_data.page} dari {paginated_data.pages}",
        data=[record.to_dict() for record in records],
        meta=meta
    )


@bp.route("/<string:biometric_id>", methods=["GET"])
@require_api_key
def get_biometric(biometric_id: str):
    """
    Mendapatkan detail data biometrik berdasarkan ID.

    Args:
        biometric_id: ID data biometrik.

    Response:
        - 200: Detail data biometrik
        - 404: Data tidak ditemukan
    """
    record = BiometricData.query.get(biometric_id)
    if record is None:
        return not_found_response(
            message=f"Data biometrik dengan ID {biometric_id} tidak ditemukan"
        )

    return success_response(
        message="Data biometrik ditemukan",
        data=record.to_dict()
    )


# ──────────────────────────────────────────────
# Error handlers untuk blueprint
# ──────────────────────────────────────────────

@bp.errorhandler(413)
def request_entity_too_large(error):
    """Handler untuk file terlalu besar."""
    return error_response(
        message="Ukuran file terlalu besar. Maksimal 16MB.",
        status_code=413
    )


@bp.errorhandler(500)
def internal_server_error(error):
    """Handler untuk internal server error."""
    return error_response(
        message="Terjadi kesalahan pada server",
        status_code=500
    )
