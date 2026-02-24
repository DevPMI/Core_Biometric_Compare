"""
Flask App Factory
==================
Membuat dan mengkonfigurasi aplikasi Flask menggunakan Application Factory pattern.
"""

import os
from flask import Flask
from app.config import Config
from app.extensions import db, migrate


def create_app(config_class=Config):
    """
    Membuat instance Flask application.

    Args:
        config_class: Kelas konfigurasi yang digunakan.

    Returns:
        Flask: Instance aplikasi Flask yang sudah dikonfigurasi.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Pastikan folder upload tersedia
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Inisialisasi ekstensi
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models agar dikenali oleh SQLAlchemy
    from app.models import biometric  # noqa: F401

    # Register blueprints
    from app.api import register_blueprints
    register_blueprints(app)

    # Register CLI commands
    from app.cli import register_commands
    register_commands(app)

    # Buat tabel database jika belum ada
    with app.app_context():
        db.create_all()

    return app
