#!/usr/bin/env python3
"""Tests for public contact form persistence."""

import unittest
import json
import os
from unittest.mock import patch
from flask import Flask
import sys

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

    @patch.dict(os.environ, {"FIKIRI_INTAKE_LEAD_OWNER_USER_ID": "1"}, clear=False)
    @patch("core.contact_api.CONTACT_FROM_EMAIL", "noreply@test.com")
    @patch("core.contact_api.CONTACT_TO_EMAIL", "info@test.com")
    @patch("core.contact_api.check_public_intake_rate_limit")
    @patch("core.contact_api._send_contact_email")
    @patch("crm.service.enhanced_crm_service")
    def test_submit_intake_creates_lead(self, mock_crm, mock_send, mock_rl, *_):
        from core.rate_limiter import RateLimitResult

        mock_rl.return_value = RateLimitResult(
            allowed=True, remaining=9, reset_time=0, retry_after=0, limit=10
        )
        mock_send.return_value = True
        mock_crm.create_lead.return_value = {"success": True, "data": {"lead_id": 99}}

        payload = {
            "business_name": "Acme Co",
            "contact_name": "Jane Doe",
            "email": "jane@acme.com",
            "source": "Referral",
            "workflow_focus": "Inquiry to paid job",
        }
        response = self.client.post("/api/intake", json=payload)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        data = json.loads(response.data)
        self.assertTrue(data.get("success"))
        mock_crm.create_lead.assert_called()
        args = mock_crm.create_lead.call_args[0]
        self.assertEqual(args[0], 1)
        self.assertEqual(args[1]["email"], "jane@acme.com")
        self.assertIn("Acme", args[1].get("company", ""))

    @patch("core.contact_api.check_public_intake_rate_limit")
    @patch("core.contact_api._send_contact_email")
    def test_intake_honeypot_succeeds_without_crm(self, mock_send, mock_rl, *_):
        from core.rate_limiter import RateLimitResult

        mock_rl.return_value = RateLimitResult(
            allowed=True, remaining=9, reset_time=0, retry_after=0, limit=10
        )
        payload = {
            "business_name": "Bot Inc",
            "contact_name": "Bot",
            "email": "bot@example.com",
            "leave_blank": "filled-by-bot",
        }
        response = self.client.post("/api/intake", json=payload)
        self.assertEqual(response.status_code, 200)
        mock_send.assert_not_called()


if __name__ == "__main__":
    unittest.main()

