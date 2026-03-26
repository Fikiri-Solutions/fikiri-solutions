#!/usr/bin/env python3
"""Tests for public contact form persistence."""

import unittest
import json
from unittest.mock import patch
from flask import Flask
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.contact_api import contact_bp


class TestContactApi(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(contact_bp)
        self.client = self.app.test_client()

    @patch("core.contact_api.CONTACT_FROM_EMAIL", "noreply@test.com")
    @patch("core.contact_api.CONTACT_TO_EMAIL", "info@test.com")
    @patch("core.contact_api.db_optimizer")
    @patch("core.contact_api._send_contact_email")
    def test_submit_contact_success_persists(self, mock_send, mock_db, *_):
        mock_send.return_value = True
        mock_db.execute_query.return_value = None

        payload = {
            "name": "Jane Smith",
            "email": "jane@example.com",
            "phone": "+15550001111",
            "company": "Acme",
            "subject": "Pricing",
            "message": "Hi there",
        }

        response = self.client.post("/api/contact", json=payload)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertTrue(data.get("success"))

        # Best-effort: verify we attempted to insert a row.
        self.assertTrue(mock_db.execute_query.called)
        _q, params = mock_db.execute_query.call_args[0]
        self.assertIn("jane@example.com", params)

    @patch("core.contact_api.CONTACT_FROM_EMAIL", "noreply@test.com")
    @patch("core.contact_api.CONTACT_TO_EMAIL", "info@test.com")
    @patch("core.contact_api.db_optimizer")
    @patch("core.contact_api._send_contact_email")
    def test_submit_contact_failure_persists_with_failed_status(
        self, mock_send, mock_db, *_,
    ):
        mock_send.return_value = False
        mock_db.execute_query.return_value = None

        payload = {
            "name": "Jane Smith",
            "email": "jane@example.com",
            "message": "Hi there",
        }

        response = self.client.post("/api/contact", json=payload)
        self.assertEqual(response.status_code, 503)

        data = json.loads(response.data)
        self.assertFalse(data.get("success"))

        self.assertTrue(mock_db.execute_query.called)
        _q, params = mock_db.execute_query.call_args[0]
        self.assertIn("failed", params)


if __name__ == "__main__":
    unittest.main()

