#!/usr/bin/env python3
"""
Secure Sessions Unit Tests
Tests for core/secure_sessions.py (create_session, get_session, validation)
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

from flask import Flask, g

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


class TestSecureSessionManager(unittest.TestCase):
    def setUp(self):
        with patch("core.secure_sessions.REDIS_AVAILABLE", False):
            with patch("core.secure_sessions.db_optimizer") as mock_db:
                mock_db.execute_query.return_value = None
                from core.secure_sessions import SecureSessionManager

                self.manager = SecureSessionManager()
                self.manager.redis_client = None

    @patch("core.secure_sessions.db_optimizer")
    def test_create_session_returns_session_id_and_cookie(self, mock_db):
        mock_db.execute_query.return_value = None
        session_id, cookie_data = self.manager.create_session(
            user_id=1,
            user_data={"email": "u@t.com", "name": "User"},
            ip_address="127.0.0.1",
            user_agent="test",
        )
        self.assertIsInstance(session_id, str)
        self.assertGreater(len(session_id), 10)
        self.assertIsInstance(cookie_data, dict)
        self.assertIn("key", cookie_data)
        self.assertIn("value", cookie_data)

    def test_get_session_returns_none_for_empty_id(self):
        self.assertIsNone(self.manager.get_session(""))
        self.assertIsNone(self.manager.get_session(None))

    @patch("core.secure_sessions.db_optimizer")
    def test_get_session_fallback_to_db(self, mock_db):
        mock_db.execute_query.return_value = [
            {
                "id": 1,
                "session_id": "abc123",
                "user_id": 1,
                "ip_address": "127.0.0.1",
                "user_agent": "test",
                "created_at": "2024-01-01T00:00:00",
                "last_accessed": "2024-01-01T00:00:00",
                "expires_at": "2025-01-01T00:00:00",
                "is_active": True,
                "metadata": '{"user_data": {"email": "u@t.com"}}',
            }
        ]
        data = self.manager.get_session("abc123")
        self.assertIsNotNone(data)
        self.assertEqual(data.get("user_id"), 1)
        self.assertIn("user_data", data)

    @patch("core.secure_sessions.db_optimizer")
    def test_get_session_expired_returns_none(self, mock_db):
        mock_db.execute_query.return_value = []
        self.assertIsNone(self.manager.get_session("expired_session_id"))


class TestLoadSecureSessionJwtFallback(unittest.TestCase):
    """Bearer JWT populates g.user_id when no session cookie (API client pattern)."""

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("core.secure_sessions.db_optimizer")
    def test_bearer_jwt_sets_g_user_id(self, mock_db, mock_get_jwt):
        mock_db.execute_query.return_value = None
        mock_get_jwt.return_value.verify_access_token.return_value = {
            "user_id": 99,
            "type": "access",
        }

        from core.secure_sessions import init_secure_sessions

        app = Flask(__name__)
        app.config["TESTING"] = True
        init_secure_sessions(app)

        @app.route("/probe")
        def probe():
            return {"user_id": g.user_id}

        with app.test_client() as client:
            rv = client.get("/probe", headers={"Authorization": "Bearer testtoken"})
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(rv.get_json().get("user_id"), 99)


if __name__ == "__main__":
    unittest.main()
