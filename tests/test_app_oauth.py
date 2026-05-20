#!/usr/bin/env python3
"""
OAuth Blueprint Unit Tests
Tests for core/app_oauth.py
"""

import json
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
        mock_db.upsert_oauth_state_row.assert_called_once()
        args = mock_db.upsert_oauth_state_row.call_args.args
        self.assertEqual(args[0], "state_123")
        self.assertIsNone(args[1])
        self.assertEqual(args[2], "gmail")

    def test_gmail_start_persists_bearer_user_id(self):
        app = _create_app()
        jwt_mgr = MagicMock()
        jwt_mgr.verify_access_token.return_value = {"user_id": 7}
        with patch("core.app_oauth.GOOGLE_CLIENT_ID", "client"), patch(
            "core.app_oauth.GOOGLE_CLIENT_SECRET", "secret"
        ), patch("core.app_oauth.secrets.token_urlsafe", return_value="state_123"), patch(
            "core.jwt_auth.get_jwt_manager", return_value=jwt_mgr
        ), patch("core.database_optimization.db_optimizer") as mock_db:
            client = app.test_client()
            resp = client.get(
                "/api/oauth/gmail/start?redirect=/next",
                headers={"Authorization": "Bearer access"},
            )

        self.assertEqual(resp.status_code, 200)
        args = mock_db.upsert_oauth_state_row.call_args.args
        self.assertEqual(args[1], 7)

    def test_gmail_start_stores_lookback_days_query_param(self):
        app = _create_app()
        with patch("core.app_oauth.GOOGLE_CLIENT_ID", "client"), patch(
            "core.app_oauth.GOOGLE_CLIENT_SECRET", "secret"
        ), patch("core.app_oauth.secrets.token_urlsafe", return_value="state_days"), patch(
            "core.database_optimization.db_optimizer"
        ) as mock_db:
            client = app.test_client()
            resp = client.get(
                "/api/oauth/gmail/start?redirect=/integrations/gmail&lookback_days=365"
            )

        self.assertEqual(resp.status_code, 200)
        metadata_json = mock_db.upsert_oauth_state_row.call_args.kwargs.get("metadata_json")
        if metadata_json is None:
            metadata_json = mock_db.upsert_oauth_state_row.call_args.args[5]
        metadata = json.loads(metadata_json)
        self.assertEqual(metadata.get("lookback_days"), 365)
        self.assertEqual(metadata.get("lookback_preset"), "1y")

    def test_gmail_start_stores_lookback_in_oauth_metadata(self):
        app = _create_app()
        with patch("core.app_oauth.GOOGLE_CLIENT_ID", "client"), patch(
            "core.app_oauth.GOOGLE_CLIENT_SECRET", "secret"
        ), patch("core.app_oauth.secrets.token_urlsafe", return_value="state_lb"), patch(
            "core.database_optimization.db_optimizer"
        ) as mock_db:
            client = app.test_client()
            resp = client.get("/api/oauth/gmail/start?redirect=/integrations/gmail&lookback=1y")

        self.assertEqual(resp.status_code, 200)
        metadata_json = mock_db.upsert_oauth_state_row.call_args.kwargs.get("metadata_json")
        if metadata_json is None:
            metadata_json = mock_db.upsert_oauth_state_row.call_args.args[5]
        metadata = json.loads(metadata_json)
        self.assertEqual(metadata.get("lookback_days"), 365)
        self.assertEqual(metadata.get("lookback_preset"), "1y")

    def test_gmail_start_invalid_lookback_defaults_to_90d(self):
        app = _create_app()
        with patch("core.app_oauth.GOOGLE_CLIENT_ID", "client"), patch(
            "core.app_oauth.GOOGLE_CLIENT_SECRET", "secret"
        ), patch("core.app_oauth.secrets.token_urlsafe", return_value="state_def"), patch(
            "core.database_optimization.db_optimizer"
        ) as mock_db:
            client = app.test_client()
            resp = client.get("/api/oauth/gmail/start?lookback=not-a-preset")

        self.assertEqual(resp.status_code, 200)
        metadata_json = mock_db.upsert_oauth_state_row.call_args.kwargs.get("metadata_json")
        if metadata_json is None:
            metadata_json = mock_db.upsert_oauth_state_row.call_args.args[5]
        metadata = json.loads(metadata_json)
        self.assertEqual(metadata.get("lookback_days"), 90)
        self.assertEqual(metadata.get("lookback_preset"), "90d")

    def test_gmail_callback_passes_lookback_to_first_sync_queue(self):
        app = _create_app()
        oauth_metadata = json.dumps(
            {"user_id": 42, "lookback_days": 365, "lookback_preset": "1y"}
        )
        token_response = MagicMock()
        token_response.json.return_value = {
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_in": 3600,
        }
        userinfo_response = MagicMock()
        userinfo_response.status_code = 200
        userinfo_response.json.return_value = {"id": "google-sub", "email": "u@example.com"}

        with patch("core.app_oauth.GOOGLE_CLIENT_ID", "client"), patch(
            "core.app_oauth.GOOGLE_CLIENT_SECRET", "secret"
        ), patch("core.app_oauth.encrypt", side_effect=lambda x: x), patch(
            "core.app_oauth.upsert_gmail_tokens"
        ), patch("core.app_oauth.merge_user_google_sub"), patch(
            "core.database_optimization.db_optimizer"
        ) as mock_db, patch("requests.post", return_value=token_response), patch(
            "requests.get", return_value=userinfo_response
        ), patch("core.onboarding_jobs.onboarding_job_manager") as mock_jobs:
            mock_db.execute_query.side_effect = [
                [
                    {
                        "state": "expected",
                        "redirect_url": "/integrations/gmail",
                        "user_id": 42,
                        "metadata": oauth_metadata,
                    }
                ],
                None,
                [{"onboarding_step": 2, "onboarding_completed": False}],
            ]
            client = app.test_client()
            resp = client.get("/api/oauth/gmail/callback?state=expected&code=abc")

        self.assertEqual(resp.status_code, 302)
        mock_jobs.queue_first_sync_job.assert_called_once_with(42, lookback_days=365)

    def test_outlook_start_persists_bearer_user_id(self):
        app = _create_app()
        jwt_mgr = MagicMock()
        jwt_mgr.verify_access_token.return_value = {"user_id": 8}
        with patch("core.app_oauth.MICROSOFT_CLIENT_ID", "client"), patch(
            "core.app_oauth.MICROSOFT_CLIENT_SECRET", "secret"
        ), patch("core.app_oauth.secrets.token_urlsafe", return_value="state_456"), patch(
            "core.jwt_auth.get_jwt_manager", return_value=jwt_mgr
        ), patch("core.database_optimization.db_optimizer") as mock_db:
            client = app.test_client()
            resp = client.get(
                "/api/oauth/outlook/start?redirect=/next",
                headers={"Authorization": "Bearer access"},
            )

        self.assertEqual(resp.status_code, 200)
        args = mock_db.upsert_oauth_state_row.call_args.args
        self.assertEqual(args[1], 8)
        self.assertEqual(args[2], "outlook")

    def test_gmail_callback_state_mismatch(self):
        app = _create_app()

        @app.before_request
        def _set_state():
            g.session_data = {"oauth_state": "expected"}

        client = app.test_client()
        resp = client.get("/api/oauth/gmail/callback?state=bad")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json().get("error"), "state_mismatch")

    def test_gmail_callback_missing_state_in_db_returns_400_not_500(self):
        """When session has no oauth_state and DB has no row, must not IndexError (regression)."""
        app = _create_app()

        with patch("core.database_optimization.db_optimizer") as mock_db:
            mock_db.execute_query.return_value = []
            client = app.test_client()
            resp = client.get("/api/oauth/gmail/callback?state=some_state_from_google&code=unused")

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
