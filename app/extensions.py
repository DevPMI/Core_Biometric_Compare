"""
Extensions
==========
Inisialisasi ekstensi Flask yang digunakan secara global.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()
