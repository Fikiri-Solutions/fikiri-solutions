#!/usr/bin/env python3
"""
OAuth Blueprint Unit Tests
Tests for core/app_oauth.py
"""

import unittest
import os
import sys
from unittest.mock import MagicMock, patch

from flask import Flask, g

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

from core import app_oauth


def _create_app():
    app = Flask(__name__)
    app.secret_key = "test"
    app.register_blueprint(app_oauth.oauth)

    @app.before_request
    def _set_session_data():
        g.session_data = {}

    return app


class TestAppOAuth(unittest.TestCase):
    def test_encrypt_decrypt_roundtrip(self):
        value = "secret-token"
        encrypted = app_oauth.encrypt(value)
        decrypted = app_oauth.decrypt(encrypted)
        self.assertEqual(decrypted, value)

    def test_gmail_start_missing_config(self):
        app = _create_app()
        with patch("core.app_oauth.GOOGLE_CLIENT_ID", None), patch("core.app_oauth.GOOGLE_CLIENT_SECRET", None):
            client = app.test_client()
            resp = client.get("/api/oauth/gmail/start")
        self.assertEqual(resp.status_code, 500)
        self.assertIn("OAuth not configured", resp.get_json().get("error", ""))

    def test_gmail_start_returns_url_and_persists_state(self):
        app = _create_app()
        with patch("core.app_oauth.GOOGLE_CLIENT_ID", "client"), patch(
            "core.app_oauth.GOOGLE_CLIENT_SECRET", "secret"
        ):
            with patch("core.app_oauth.secrets.token_urlsafe", return_value="state_123"):
                with patch("core.database_optimization.db_optimizer") as mock_db:
                    client = app.test_client()
                    resp = client.get("/api/oauth/gmail/start?redirect=/next")

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("state_123", data.get("url", ""))
        mock_db.execute_query.assert_called_once()

    def test_gmail_callback_state_mismatch(self):
        app = _create_app()

        @app.before_request
        def _set_state():
            g.session_data = {"oauth_state": "expected"}

        client = app.test_client()
        resp = client.get("/api/oauth/gmail/callback?state=bad")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json().get("error"), "state_mismatch")

    def test_gmail_callback_missing_code(self):
        app = _create_app()

        @app.before_request
        def _set_state():
            g.session_data = {"oauth_state": "expected"}

        client = app.test_client()
        resp = client.get("/api/oauth/gmail/callback?state=expected")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json().get("error"), "missing_code")

    def test_gmail_callback_token_exchange_error(self):
        app = _create_app()

        @app.before_request
        def _set_state():
            g.session_data = {"oauth_state": "expected"}

        token_response = MagicMock()
        token_response.json.return_value = {"error": "invalid_grant", "error_description": "bad code"}

        with patch("core.app_oauth.GOOGLE_CLIENT_ID", "client"), patch(
            "core.app_oauth.GOOGLE_CLIENT_SECRET", "secret"
        ):
            with patch("requests.post", return_value=token_response):
                client = app.test_client()
                resp = client.get("/api/oauth/gmail/callback?state=expected&code=abc")

        self.assertEqual(resp.status_code, 400)
        body = resp.get_json()
        self.assertEqual(body.get("error"), "invalid_grant")
        self.assertIn("authorization code", body.get("message", "").lower())

    def test_upsert_gmail_tokens_insert_and_update(self):
        payload = {
            "access_token": "enc_access",
            "refresh_token": "enc_refresh",
            "expiry": 123,
            "scopes": ["scope"],
        }
        with patch("core.database_optimization.db_optimizer") as mock_db:
            mock_db.execute_query.side_effect = [[], None]
            app_oauth.upsert_gmail_tokens(user_id=1, **payload)
            self.assertEqual(mock_db.execute_query.call_count, 2)

        with patch("core.database_optimization.db_optimizer") as mock_db:
            mock_db.execute_query.side_effect = [[{"id": 1}], None]
            app_oauth.upsert_gmail_tokens(user_id=2, **payload)
            self.assertEqual(mock_db.execute_query.call_count, 2)


if __name__ == "__main__":
    unittest.main()
