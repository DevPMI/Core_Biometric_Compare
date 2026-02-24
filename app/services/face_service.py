"""
Face Recognition Service
=========================
Menggunakan DeepFace untuk ekstraksi embedding wajah
dan perbandingan (cosine similarity).
"""

import json
import logging
import numpy as np
from deepface import DeepFace
from flask import current_app

logger = logging.getLogger(__name__)


def extract_face_embedding(image_data: str | np.ndarray) -> list | None:
    """
    Mengekstrak embedding vector dari gambar wajah.

    Args:
        image_data: Path absolut ke file gambar wajah string ATAU numpy array gambar.

    Returns:
        list: Embedding vector sebagai list float, atau None jika gagal.
    """
    try:
        model_name = current_app.config.get("FACE_MODEL", "VGG-Face")
        
        # DeepFace.represent handles both path string and numpy array in 'img_path'
        # enforce_detection=True ensures we reject images without a clear face (e.g. palm, object)
        # Menggunakan backend 'opencv' (Haar Cascades) untuk KECEPATAN (Akses Pintu Harian).
        # Ini jauh lebih ringan di CPU dibanding RetinaFace, waktu respons bisa turun ke ~1-2 detik.
        embeddings = DeepFace.represent(
            img_path=image_data,
            model_name=model_name,
            enforce_detection=True,
            detector_backend="opencv"
        )

        if embeddings and len(embeddings) > 0:
            embedding = embeddings[0]["embedding"]
            logger.info(
                "Berhasil mengekstrak embedding wajah: %d dimensi",
                len(embedding)
            )
            return embedding

        logger.warning("Tidak ada wajah terdeteksi pada gambar")
        return None

    except Exception as e:
        logger.error("Gagal mengekstrak embedding wajah: %s", str(e))
        return None


def compare_face_embeddings(
    input_embedding: list,
    stored_embedding_json: str,
    threshold: float | None = None
) -> tuple[bool, float]:
    """
    Membandingkan dua embedding wajah menggunakan cosine similarity.

    Args:
        input_embedding: Embedding dari gambar input.
        stored_embedding_json: JSON string embedding tersimpan di database.
        threshold: Batas minimal similarity (opsional, ambil dari config).

    Returns:
        tuple: (is_match: bool, similarity_score: float)
    """
    try:
        if threshold is None:
            threshold = current_app.config.get("FACE_THRESHOLD", 0.40)

        stored_embedding = json.loads(stored_embedding_json)

        vec_a = np.array(input_embedding, dtype=np.float64)
        vec_b = np.array(stored_embedding, dtype=np.float64)

        # Cosine similarity
        dot_product = np.dot(vec_a, vec_b)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)

        if norm_a == 0 or norm_b == 0:
            return False, 0.0

        cosine_similarity = dot_product / (norm_a * norm_b)

        # Cosine distance (DeepFace menggunakan cosine distance)
        cosine_distance = 1.0 - cosine_similarity

        is_match = cosine_distance <= threshold

        logger.debug(
            "Perbandingan wajah - distance: %.4f, threshold: %.4f, cocok: %s",
            cosine_distance, threshold, is_match
        )

        return is_match, cosine_distance

    except Exception as e:
        logger.error("Gagal membandingkan embedding wajah: %s", str(e))
        return False, 1.0


def serialize_embedding(embedding: list) -> str:
    """Mengubah embedding vector menjadi JSON string untuk disimpan di database."""
    return json.dumps(embedding)
