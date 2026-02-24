"""
API Blueprint Registration
============================
Mendaftarkan semua blueprint API ke aplikasi Flask.
"""

from flask import Flask


def register_blueprints(app: Flask):
    """Mendaftarkan semua blueprint ke aplikasi."""
    from app.api.biometric import bp as biometric_bp
    app.register_blueprint(biometric_bp)
