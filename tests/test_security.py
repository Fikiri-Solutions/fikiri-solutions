"""
Unit tests for core/security.py (init_security, require_auth, SecurityUtils).
"""

import os
import sys
from unittest.mock import patch, MagicMock

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request


class TestSecurityUtils:
    """Test SecurityUtils static methods (pure)."""

    def test_sanitize_input_string_removes_dangerous_chars(self):
        from core.security import SecurityUtils
        out = SecurityUtils.sanitize_input("hello <script> world")
        assert "<" not in out and ">" not in out
        assert "hello" in out and "script" in out and "world" in out

    def test_sanitize_input_dict_recursive(self):
        from core.security import SecurityUtils
        out = SecurityUtils.sanitize_input({"a": "<b>", "c": "safe"})
        assert out["a"] == "b"
        assert out["c"] == "safe"

    def test_sanitize_input_list_recursive(self):
        from core.security import SecurityUtils
        out = SecurityUtils.sanitize_input(["<x>", "y"])
        assert out[0] == "x"
        assert out[1] == "y"

    def test_validate_email_valid(self):
        from core.security import SecurityUtils
        assert SecurityUtils.validate_email("user@example.com") is True
        assert SecurityUtils.validate_email("a.b@co.uk") is True

    def test_validate_email_invalid(self):
        from core.security import SecurityUtils
        assert SecurityUtils.validate_email("notanemail") is False
        assert SecurityUtils.validate_email("@nodomain.com") is False
        assert SecurityUtils.validate_email("missing@") is False


class TestRequireAuth:
    """Test require_auth decorator."""

    def test_require_auth_missing_header_returns_401(self):
        from core.security import require_auth
        app = Flask(__name__)
        @app.route("/protected")
        @require_auth
        def protected():
            return {"ok": True}
        with app.test_client() as c:
            r = c.get("/protected")
        assert r.status_code == 401
        data = r.get_json()
        assert data and (data.get("error_code") == "AUTHENTICATION_REQUIRED" or "auth" in str(data).lower())

    def test_require_auth_no_bearer_prefix_returns_401(self):
        from core.security import require_auth
        app = Flask(__name__)
        @app.route("/protected")
        @require_auth
        def protected():
            return {"ok": True}
        with app.test_client() as c:
            r = c.get("/protected", headers={"Authorization": "Invalid token"})
        assert r.status_code == 401


class TestInitSecurity:
    """Test init_security(app) attaches middleware and returns app."""

    @patch("core.security.CORS")
    @patch("core.security.Limiter")
    def test_init_security_returns_app(self, mock_limiter_class, mock_cors):
        mock_limiter_class.return_value.init_app = MagicMock()
        from core.security import init_security
        if not getattr(init_security, "__wrapped__", True):
            pass
        app = Flask(__name__)
        result = init_security(app)
        assert result is app
