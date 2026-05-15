#!/usr/bin/env python3
"""Integration routes JWT user_id regression tests."""

import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

from flask import Flask
from routes.integrations import integrations_bp


class TestIntegrationsJwtUserId(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(integrations_bp)
        self.client = self.app.test_client()

    @patch("routes.integrations.integration_manager")
    @patch("core.jwt_auth.get_jwt_manager")
    def test_google_calendar_status_uses_jwt_user_id(self, mock_jwt, mock_im):
        mock_jwt.return_value.verify_access_token.return_value = {"user_id": 42, "type": "access"}
        mock_im.get_status.return_value = {"connected": False}
        response = self.client.get(
            "/api/integrations/google-calendar/status",
            headers={"Authorization": "Bearer t"},
        )
        self.assertEqual(response.status_code, 200)
        mock_im.get_status.assert_called_once_with(42, "google_calendar")


if __name__ == "__main__":
    unittest.main()
