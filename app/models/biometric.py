"""
Model BiometricData
====================
Menyimpan data biometrik (wajah/telapak tangan) beserta
embedding/deskriptor untuk proses perbandingan.
"""

from datetime import datetime, timezone
from app.extensions import db


class BiometricData(db.Model):
    """Model untuk menyimpan data biometrik pengguna."""

    __tablename__ = "biometric_data"

    id = db.Column(db.String(50), primary_key=True)
    biometric_type = db.Column(
        db.String(10),
        nullable=False,
        index=True,
        comment="Tipe biometrik: 'face' atau 'palm'"
    )
    image_path = db.Column(
        db.String(500),
        nullable=False,
        comment="Path ke file gambar referensi"
    )
    embedding = db.Column(
        db.Text,
        nullable=False,
        comment="JSON: face embedding vector atau palm ORB descriptors"
    )
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self):
        return f"<BiometricData id={self.id} type={self.biometric_type}>"

    def to_dict(self):
        """Konversi model ke dictionary untuk response API."""
        return {
            "id": self.id,
            "biometric_type": self.biometric_type,
            "image_path": self.image_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
