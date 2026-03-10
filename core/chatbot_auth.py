"""
Auth for chatbot KB admin: allow either logged-in user (JWT/session) or X-API-Key.
So you can manage your own FAQ/chatbot from the dashboard without an API key.
"""

from functools import wraps
from flask import request, jsonify, g

from core.secure_sessions import get_current_user_id


def require_api_key_or_jwt(f):
    """Require either a logged-in user (JWT/session) or a valid X-API-Key header."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_current_user_id()
        if user_id is not None:
            g.api_key_info = {"user_id": user_id, "tenant_id": str(user_id)}
            return f(*args, **kwargs)
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
        if api_key and isinstance(api_key, str) and api_key.startswith("Bearer "):
            api_key = api_key[7:]
        if not api_key:
            return jsonify({
                "success": False,
                "error": "Log in or provide X-API-Key",
                "error_code": "AUTH_REQUIRED"
            }), 401
        from core.api_key_manager import api_key_manager
        key_info = api_key_manager.validate_api_key(api_key)
        if not key_info:
            return jsonify({
                "success": False,
                "error": "Invalid or expired API key",
                "error_code": "INVALID_API_KEY"
            }), 401
        if "chatbot:query" not in set(key_info.get("scopes", [])):
            return jsonify({
                "success": False,
                "error": "Insufficient permissions",
                "error_code": "INSUFFICIENT_SCOPE"
            }), 403
        g.api_key_info = key_info
        g.api_key_id = key_info.get("api_key_id")
        g.api_key = api_key
        return f(*args, **kwargs)

    return decorated_function
