#!/usr/bin/env python3
"""User customization routes tests (logo upload)."""

import unittest
import io
import json
from unittest.mock import patch, MagicMock
import sys
import os
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.user import user_bp


def _auth_headers():
    return {"Authorization": "Bearer testtoken"}


class TestUserCustomizationLogoRoutes(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.register_blueprint(user_bp)
        self.client = self.app.test_client()

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("routes.user.get_current_user_id", return_value=1)
    @patch("routes.user.db_optimizer")
    def test_get_logo_returns_none_when_missing(self, mock_db, mock_user_id, mock_mgr):
        mock_mgr.return_value.verify_access_token.return_value = {"user_id": 1}
        mock_db.execute_query.return_value = []

        response = self.client.get(
            "/api/user/customization/logo",
            headers=_auth_headers(),
        )
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        customization = data.get("data", {}).get("customization", {})
        self.assertIn("logoUrl", customization)
        self.assertIsNone(customization.get("logoUrl"))

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("routes.user.get_current_user_id", return_value=1)
    @patch("routes.user.db_optimizer")
    @patch("routes.user.log_activity_event")
    def test_upload_logo_success(self, mock_log, mock_db, mock_user_id, mock_mgr):
        mock_mgr.return_value.verify_access_token.return_value = {"user_id": 1}
        mock_db.execute_query.return_value = None

        png_bytes = b"\x89PNG\r\n\x1a\n" + b"test"
        file_obj = (io.BytesIO(png_bytes), "logo.png")

        response = self.client.post(
            "/api/user/customization/logo",
            headers=_auth_headers(),
            data={"file": file_obj},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        customization = data.get("data", {}).get("customization", {})
        logo_url = customization.get("logoUrl")
        self.assertIsInstance(logo_url, str)
        self.assertTrue(logo_url.startswith("data:image/png;base64,"))

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("routes.user.get_current_user_id", return_value=1)
    def test_upload_logo_rejects_invalid_type(self, mock_user_id, mock_mgr):
        mock_mgr.return_value.verify_access_token.return_value = {"user_id": 1}

        txt_bytes = b"not a logo"
        file_obj = (io.BytesIO(txt_bytes), "logo.txt")

        response = self.client.post(
            "/api/user/customization/logo",
            headers=_auth_headers(),
            data={"file": file_obj},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)

        data = json.loads(response.data)
        self.assertEqual(data.get("code"), "INVALID_FILE_TYPE")

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("routes.user.get_current_user_id", return_value=1)
    @patch("routes.user.db_optimizer")
    def test_delete_logo_persists_cleared_state(self, mock_db, mock_user_id, mock_mgr):
        mock_mgr.return_value.verify_access_token.return_value = {"user_id": 1}
        mock_db.execute_query.return_value = None

        response = self.client.delete(
            "/api/user/customization/logo",
            headers=_auth_headers(),
        )
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        customization = data.get("data", {}).get("customization", {})
        self.assertIsNone(customization.get("logoUrl"))


if __name__ == "__main__":
    unittest.main()

