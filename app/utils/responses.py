"""
Utilitas Response API
======================
Helper functions untuk menghasilkan response JSON yang konsisten.
"""

from flask import jsonify


def success_response(data=None, message="Berhasil", status_code=200, meta=None):
    """
    Menghasilkan response sukses yang terstandarisasi.

    Args:
        data: Data yang dikembalikan (opsional).
        message: Pesan sukses.
        status_code: HTTP status code.
        meta: Informasi tambahan seperti pagination (opsional).

    Returns:
        tuple: (Response JSON, status_code)
    """
    response = {
        "success": True,
        "message": message,
    }
    if data is not None:
        response["data"] = data
    if meta is not None:
        response["meta"] = meta
        
    return jsonify(response), status_code


def error_response(message="Terjadi kesalahan", status_code=400, errors=None):
    """
    Menghasilkan response error yang terstandarisasi.

    Args:
        message: Pesan error.
        status_code: HTTP status code.
        errors: Detail error tambahan (opsional).

    Returns:
        tuple: (Response JSON, status_code)
    """
    response = {
        "success": False,
        "message": message,
    }
    if errors is not None:
        response["errors"] = errors
    return jsonify(response), status_code


def not_found_response(message="Data tidak ditemukan"):
    """
    Menghasilkan response 404 Not Found.

    Args:
        message: Pesan not found.

    Returns:
        tuple: (Response JSON, 404)
    """
    return error_response(message=message, status_code=404)


def created_response(data=None, message="Data berhasil ditambahkan"):
    """
    Menghasilkan response 201 Created.

    Args:
        data: Data yang baru dibuat.
        message: Pesan sukses.

    Returns:
        tuple: (Response JSON, 201)
    """
    return success_response(data=data, message=message, status_code=201)
