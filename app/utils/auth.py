"""
Authentication Utilities
========================
Middleware dan fungsi bantuan untuk keamanan.
"""

from functools import wraps
from flask import request, current_app
from app.utils.responses import error_response


def require_api_key(f):
    """
    Decorator untuk memvalidasi header x-api-key pada request.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Ambil api key dari header request
        api_key = request.headers.get("x-api-key")
        
        # Ambil api key yang valid dari konfigurasi server
        valid_api_key = current_app.config.get("API_KEY")

        if not valid_api_key:
            # Server belum dikonfigurasi dengan API_KEY
            return error_response(
                message="Server configuration error: API_KEY is not set", 
                status_code=500
            )

        if not api_key:
            return error_response(
                message="Unauthorized: Missing x-api-key header", 
                status_code=401
            )
            
        if api_key != valid_api_key:
            return error_response(
                message="Unauthorized: Invalid x-api-key", 
                status_code=401
            )

        return f(*args, **kwargs)
    return decorated_function
