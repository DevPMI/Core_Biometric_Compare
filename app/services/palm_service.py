"""
Palm Vein Recognition Service
==============================
Menggunakan OpenCV ORB feature extraction dan BFMatcher
untuk mencocokkan pola vena telapak tangan dari gambar hitam-putih.
"""

import json
import logging
import cv2
import numpy as np
from deepface import DeepFace
from flask import current_app

logger = logging.getLogger(__name__)


def _preprocess_image(image_data: str | np.ndarray) -> np.ndarray | None:
    """
    Memproses gambar vena menjadi format optimal untuk ekstraksi fitur.

    Args:
        image_data: Path ke file gambar (str) ATAU numpy array gambar (np.ndarray).

    Returns:
        np.ndarray: Gambar grayscale yang sudah diproses, atau None jika gagal.
    """
    try:
        if isinstance(image_data, str):
            img = cv2.imread(image_data, cv2.IMREAD_GRAYSCALE)
            if img is None:
                logger.error("Tidak dapat membaca gambar: %s", image_data)
                return None
        elif isinstance(image_data, np.ndarray):
            img = image_data
            # Jika gambar input berwarna (3 channel), convert ke grayscale
            if len(img.shape) == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            logger.error("Input gambar tidak valid (harus path atau numpy array)")
            return None

        # Resize ke ukuran standar untuk konsistensi
        img = cv2.resize(img, (400, 400))

        # CLAHE (Contrast Limited Adaptive Histogram Equalization)
        # untuk meningkatkan kontras pola vena
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        img = clahe.apply(img)

        # Gaussian blur untuk mengurangi noise
        img = cv2.GaussianBlur(img, (5, 5), 0)

        # Adaptive threshold untuk mempertegas pola vena
        img = cv2.adaptiveThreshold(
            img, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=11,
            C=2
        )

        return img

    except Exception as e:
        logger.error("Gagal memproses gambar: %s", str(e))
        return None


def extract_palm_features(image_data: str | np.ndarray) -> np.ndarray | None:
    """
    Mengekstrak deskriptor ORB dari gambar pola vena telapak tangan.
    Memastikan gambar BUKAN wajah.

    Args:
        image_data: Path absolut ke file gambar vena ATAU numpy array gambar.

    Returns:
        np.ndarray: Deskriptor ORB, atau None jika gagal atau jika WAJAH terdeteksi.
    """
    try:
        # 1. Validasi Negatif: Pastikan BUKAN wajah
        # Kita gunakan DeepFace untuk mendeteksi wajah.
        # Jika wajah terdeteksi -> Ini BUKAN palm -> Return None
        try:
            # Gunakan OpenCV untuk cek negatif (jauh lebih cepat dari RetinaFace)
            DeepFace.extract_faces(
                img_path=image_data, 
                enforce_detection=True,
                detector_backend="opencv"
            )
            logger.warning("Falsafah Palm: Wajah terdeteksi dalam gambar palm. Ditolak.")
            return None
        except ValueError:
            # ValueError means "Face could not be detected" -> Good for Palm!
            pass
        except Exception as e:
            # Ignore other errors during face check to avoid blocking valid palms on edge cases
            logger.debug("Face check verify error (ignored): %s", str(e))

        # 2. Lanjut ke ekstraksi fitur Palm (ORB)
        img = _preprocess_image(image_data)
        if img is None:
            return None

        n_features = current_app.config.get("PALM_ORB_FEATURES", 1000)

        # Inisialisasi ORB detector
        orb = cv2.ORB_create(nfeatures=n_features)
        keypoints, descriptors = orb.detectAndCompute(img, None)

        if descriptors is None or len(keypoints) == 0:
            logger.warning(
                "Tidak ada fitur yang terdeteksi pada gambar"
            )
            return None

        logger.info(
            "Berhasil mengekstrak %d fitur ORB dari gambar vena",
            len(keypoints)
        )
        return descriptors

    except Exception as e:
        logger.error("Gagal mengekstrak fitur palm: %s", str(e))
        return None





def compare_palm_features(
    input_descriptors: np.ndarray,
    stored_descriptors_json: str,
    threshold: float | None = None
) -> tuple[bool, float]:
    """
    Membandingkan deskriptor ORB dari dua gambar vena menggunakan
    BFMatcher dengan Hamming distance.

    Args:
        input_descriptors: Deskriptor dari gambar input.
        stored_descriptors_json: JSON string deskriptor dari database.
        threshold: Batas minimal rasio kecocokan (opsional).

    Returns:
        tuple: (is_match: bool, match_score: float)
    """
    try:
        if threshold is None:
            threshold = current_app.config.get("PALM_MATCH_THRESHOLD", 0.15)

        stored_descriptors = deserialize_descriptors(stored_descriptors_json)
        if stored_descriptors is None:
            return False, 0.0

        # BFMatcher dengan Hamming distance (cocok untuk ORB)
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

        # KNN matching dengan k=2 untuk Lowe's ratio test
        try:
            matches = bf.knnMatch(input_descriptors, stored_descriptors, k=2)
        except cv2.error:
            logger.warning("Gagal melakukan KNN matching")
            return False, 0.0

        # Lowe's ratio test - filter kecocokan yang bagus
        good_matches = []
        for match in matches:
            if len(match) == 2:
                m, n = match
                if m.distance < 0.75 * n.distance:
                    good_matches.append(m)

        # Hitung skor kecocokan
        total_keypoints = min(len(input_descriptors), len(stored_descriptors))
        if total_keypoints == 0:
            return False, 0.0

        match_score = len(good_matches) / total_keypoints
        is_match = match_score >= threshold

        logger.debug(
            "Perbandingan palm - good_matches: %d/%d, score: %.4f, threshold: %.4f, cocok: %s",
            len(good_matches), total_keypoints, match_score, threshold, is_match
        )

        return is_match, match_score

    except Exception as e:
        logger.error("Gagal membandingkan fitur palm: %s", str(e))
        return False, 0.0


def serialize_descriptors(descriptors: np.ndarray) -> str:
    """Mengubah deskriptor ORB menjadi JSON string untuk disimpan di database."""
    return json.dumps(descriptors.tolist())


def deserialize_descriptors(descriptors_json: str) -> np.ndarray | None:
    """Mengubah JSON string kembali menjadi numpy array deskriptor."""
    try:
        data = json.loads(descriptors_json)
        return np.array(data, dtype=np.uint8)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Gagal deserialize deskriptor: %s", str(e))
        return None
