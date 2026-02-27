"""
Liveness Service (Anti-Spoofing)
================================
Mendeteksi apakah wajah di dalam gambar merupakan wajah manusia asli (Live 3D) 
atau pemalsuan (layar HP, kertas foto).
Menggunakan model ringan MiniFASNet format ONNX.
"""

import os
import cv2
import numpy as np
import logging
import requests
import onnxruntime as ort
from flask import current_app

logger = logging.getLogger(__name__)

# Global variable to cache the ONNX session
_ort_session = None

def _get_liveness_model_path():
    """Mengambil path model dari config dan memastikan foldernya ada."""
    model_path = current_app.config.get("LIVENESS_MODEL_PATH")
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    return model_path

def download_model_if_not_exists():
    """Mengunduh model ONNX jika belum ada di server."""
    model_path = _get_liveness_model_path()
    model_url = current_app.config.get("LIVENESS_MODEL_URL")
    
    if os.path.exists(model_path):
        return

    logger.info(f"Mengunduh model Liveness Anti-Spoofing dari {model_url}...")
    try:
        response = requests.get(model_url, timeout=30)
        response.raise_for_status()
        with open(model_path, "wb") as f:
            f.write(response.content)
        logger.info(f"Model berhasil diunduh dan disimpan di {model_path}")
    except Exception as e:
        logger.error(f"Gagal mengunduh model Liveness: {e}")
        raise

def _get_ort_session():
    """Mendapatkan ONNX Runtime session, meload cuma sekali."""
    global _ort_session
    if _ort_session is None:
        download_model_if_not_exists()
        model_path = _get_liveness_model_path()
        logger.info(f"Memuat model ONNX Liveness dari {model_path}...")
        
        # Gunakan CPU Execution Provider untuk kompatibilitas docker universal dan kecepatan inferensi model < 10ms
        providers = ['CPUExecutionProvider']
        _ort_session = ort.InferenceSession(model_path, providers=providers)
    
    return _ort_session

def check_liveness(image: np.ndarray) -> tuple[bool, float]:
    """
    Memeriksa gambar apakah dari wajah manusia asli (Live) atau palsu (Spoof).
    Akan memotong gambar (crop) secara otomatis ke area kotak wajah terdekat.
    
    Returns:
        tuple[bool, float]: (is_real_human, liveness_score_0_to_1)
    """
    try:
        threshold = current_app.config.get("LIVENESS_THRESHOLD", 0.80)
        
        if image is None or image.size == 0:
            return False, 0.0

        # Gunakan Haar Cascade OpenCV untuk deteksi kotak wajah super cepat
        # Ini penting! Model liveness hanya bekerja jika inputnya benar-benar Wajah yang nge-pas, 
        # bukan gambar 640x720 yg berisi tembok/pundak.
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Ubah gambar ke Grayscale untuk deteksi kordinat wajah
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Cari wajah
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60)
        )
        
        if len(faces) == 0:
             logger.warning("[Liveness] Wajah tidak terdeteksi untuk liveness crop.")
             return False, 0.0
             
        # Ambil wajah yang paling besar (paling depan)
        (x, y, w, h) = max(faces, key=lambda rect: rect[2] * rect[3])

        # Beri sedikit 'padding' (ruang dahi/dagu) agar MiniFASNet lebih akurat membaca depth
        padding = int(w * 0.15)
        
        # Pastikan koordinat tidak melewati batas resolusi gambar
        start_y = max(0, y - padding)
        end_y = min(image.shape[0], y + h + padding)
        start_x = max(0, x - padding)
        end_x = min(image.shape[1], x + w + padding)
        
        # Lakukan pemotongan (Crop)
        face_crop_bgr = image[start_y:end_y, start_x:end_x]

        if face_crop_bgr.size == 0:
             return False, 0.0

        session = _get_ort_session()

        # Pre-processing khusus sesuai standar input MiniFASNet 2.7_80x80
        # Sesuaikan orientasi ke 80x80
        target_size = (80, 80)
        img_resized = cv2.resize(face_crop_bgr, target_size)
    
        # Normalisasi ke float32 (standar input AI vision)
        img_np = np.array(img_resized, dtype=np.float32)

        # HWC (Height, Width, Channels) to CHW (Channels, Height, Width)
        img_np = np.transpose(img_np, (2, 0, 1))

        # Tambahkan batch dimension: (1, Channels, Height, Width)
        img_np = np.expand_dims(img_np, axis=0)

        # Dapatkan nama node input
        input_name = session.get_inputs()[0].name

        # Eksekusi Inferensi ONNX
        outputs = session.run(None, {input_name: img_np})
        
        # Hasil model berupa list/array 2 elemen -> [SpoofProbability, RealProbability]
        scores = outputs[0][0]
        
        # Softmax untuk mendapatkan presentase kepastian 0.0 - 1.0
        exp_scores = np.exp(scores)
        probabilities = exp_scores / np.sum(exp_scores)
        
        # Index 1 adalah probabilitas kriteria Asli (Real)
        real_score = float(probabilities[1])
        is_real = real_score >= threshold
        
        logger.debug(f"[Liveness Check] Skor Real: {real_score:.4f} | Lulus: {is_real}")
        return is_real, real_score

    except Exception as e:
        logger.error(f"Error saat liveness inference check: {e}")
        return False, 0.0

