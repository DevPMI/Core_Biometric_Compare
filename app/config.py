"""
Konfigurasi Aplikasi
=====================
Mengatur konfigurasi untuk koneksi database, upload file,
dan parameter pengenalan biometrik.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Konfigurasi dasar aplikasi."""

    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "biometric-service-secret-key")
    API_KEY = os.getenv("API_KEY", "replace-this-api-key-in-production")

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/User_Biometrics"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload
    UPLOAD_FOLDER = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        os.getenv("UPLOAD_FOLDER", "uploads")
    )
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tiff"}

    # Face Recognition Config
    # Gunakan "ArcFace" untuk akurasi Enterprise (>99.5%)
    # Gunakan "VGG-Face" untuk legacy/lighter workload
    FACE_MODEL = os.environ.get("FACE_MODEL", "VGG-Face")
    # Threshold rekomendasi untuk ArcFace + Cosine Similarity adalah 0.68
    FACE_THRESHOLD = float(os.environ.get("FACE_THRESHOLD", "0.40"))
    
    # Liveness Detection Config
    LIVENESS_MODEL_PATH = os.environ.get("LIVENESS_MODEL_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "liveness.onnx"))
    LIVENESS_THRESHOLD = float(os.environ.get("LIVENESS_THRESHOLD", "0.80"))
    LIVENESS_MODEL_URL = "https://github.com/yakhyo/face-anti-spoofing/releases/download/weights/MiniFASNetV2.onnx"

    # Palm Vein Recognition (OpenCV ORB)
    PALM_MATCH_THRESHOLD = float(os.getenv("PALM_MATCH_THRESHOLD", 0.15))
    PALM_ORB_FEATURES = int(os.getenv("PALM_ORB_FEATURES", 1000))
