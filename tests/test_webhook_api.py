#!/usr/bin/env python3
"""
Webhook API Unit Tests
Tests for core/webhook_api.py (Tally, Typeform, intake)
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

from flask import Flask
from core.webhook_api import webhook_bp


class TestWebhookAPI(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(webhook_bp)
        self.client = self.app.test_client()

    @patch("core.webhook_api.get_webhook_service")
    def test_tally_webhook_no_service_returns_500(self, mock_get):
        mock_get.return_value = None
        response = self.client.post(
            "/api/webhooks/tally",
            json={"eventId": "e1", "data": {}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("error", data)

    @patch("core.webhook_api.get_webhook_service")
    def test_tally_webhook_no_data_returns_400(self, mock_get):
        svc = MagicMock()
        svc.config.enable_verification = False
        mock_get.return_value = svc
        response = self.client.post(
            "/api/webhooks/tally", data=None, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    @patch("core.webhook_api.get_webhook_service")
    def test_tally_webhook_success(self, mock_get):
        svc = MagicMock()
        svc.config.enable_verification = False
        svc.process_tally_webhook.return_value = {"success": True, "lead_id": 1}
        mock_get.return_value = svc
        response = self.client.post(
            "/api/webhooks/tally",
            json={"eventId": "e1", "data": {}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))

    @patch("core.webhook_api.get_webhook_service")
    def test_typeform_webhook_no_service_returns_500(self, mock_get):
        mock_get.return_value = None
        response = self.client.post(
            "/api/webhooks/typeform",
            json={"form_id": "f1", "answers": []},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)


if __name__ == "__main__":
    unittest.main()
