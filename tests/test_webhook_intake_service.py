#!/usr/bin/env python3
"""
Webhook Intake Service Unit Tests
Tests for core/webhook_intake_service.py (signature, mapping, persistence)
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


class TestWebhookIntakeService(unittest.TestCase):
    def setUp(self):
        with patch("core.webhook_intake_service.get_sheets_connector", return_value=None):
            from core.webhook_intake_service import WebhookConfig, WebhookIntakeService

            cfg = WebhookConfig(secret_key="secret", allowed_origins=["*"], enable_verification=True)
            self.service = WebhookIntakeService(cfg)

    def test_verify_webhook_signature_valid_and_invalid(self):
        payload = '{"event":"test"}'
        self.assertFalse(self.service.verify_webhook_signature(payload, "", "secret"))

        # Directly compute expected signature
        import hmac
        import hashlib

        expected = hmac.new(b"secret", payload.encode("utf-8"), hashlib.sha256).hexdigest()
        self.assertTrue(self.service.verify_webhook_signature(payload, expected, "secret"))

    def test_process_tally_webhook_missing_email(self):
        data = {"data": {"name": "Test", "message": "Hello"}}
        result = self.service.process_tally_webhook(data)
        self.assertFalse(result.get("success"))
        self.assertEqual(result.get("error"), "Email is required")

    def test_process_tally_webhook_success(self):
        captured = {}

        def _store(lead_data):
            captured.update(lead_data)
            return {"success": True, "lead_id": "lead_x"}

        self.service._store_lead_in_db = _store
        self.service.sheets_connector = MagicMock(add_lead=MagicMock(return_value={"success": True}))

        data = {"formId": "f1", "submissionId": "s1", "createdAt": "now", "data": {
            "name": "Alice",
            "email": "a@b.com",
            "phone": "123",
            "company": "ACME",
            "message": "Hi"
        }}
        result = self.service.process_tally_webhook(data)
        self.assertTrue(result.get("success"))
        self.assertIn("lead_id", result)
        self.assertEqual(captured.get("email"), "a@b.com")
        self.assertEqual(captured.get("source"), "tally")

    def test_process_typeform_webhook_maps_fields(self):
        captured = {}

        def _store(lead_data):
            captured.update(lead_data)
            return {"success": True, "lead_id": "lead_t"}

        self.service._store_lead_in_db = _store
        data = {
            "form": {"id": "form_1"},
            "form_response": {
                "token": "tok_1",
                "submitted_at": "2024-01-01T00:00:00Z",
                "answers": [
                    {"type": "email", "email": "x@y.com", "field": {"ref": "email"}},
                    {"type": "text", "text": "Bob", "field": {"ref": "full_name"}},
                    {"type": "phone_number", "phone_number": "+1-555", "field": {"ref": "phone"}},
                    {"type": "text", "text": "Fikiri", "field": {"ref": "company"}},
                    {"type": "long_text", "text": "Details", "field": {"ref": "message"}},
                ],
            },
        }
        result = self.service.process_typeform_webhook(data)
        self.assertTrue(result.get("success"))
        self.assertEqual(captured.get("email"), "x@y.com")
        self.assertEqual(captured.get("name"), "Bob")
        self.assertEqual(captured.get("company"), "Fikiri")
        self.assertEqual(captured.get("source"), "typeform")

    def test_process_generic_webhook_maps_common_fields(self):
        captured = {}

        def _store(lead_data):
            captured.update(lead_data)
            return {"success": True, "lead_id": "lead_g"}

        self.service._store_lead_in_db = _store
        data = {
            "full_name": "Gen Lead",
            "email": "gen@x.com",
            "phone_number": "555",
            "organization": "GenCo",
            "notes": "hello",
        }
        result = self.service.process_generic_webhook(data)
        self.assertTrue(result.get("success"))
        self.assertEqual(captured.get("name"), "Gen Lead")
        self.assertEqual(captured.get("email"), "gen@x.com")
        self.assertEqual(captured.get("company"), "GenCo")
        self.assertEqual(captured.get("source"), "webhook")

    def test_process_lead_sheets_failure_does_not_block(self):
        def _store(lead_data):
            return {"success": True, "lead_id": "lead_s"}

        self.service._store_lead_in_db = _store
        self.service.sheets_connector = MagicMock(
            add_lead=MagicMock(return_value={"success": False, "error": "sheets down"})
        )
        result = self.service.process_tally_webhook({"data": {"email": "a@b.com"}})
        self.assertTrue(result.get("success"))

    def test_webhook_idempotency_prevents_duplicate(self):
        calls = {"count": 0}

        def _store(lead_data):
            calls["count"] += 1
            return {"success": True, "lead_id": "lead_x"}

        class _Idem:
            def __init__(self):
                self.cached = None

            def generate_key(self, *_args, **_kwargs):
                return "k1"

            def check_key(self, _key):
                return self.cached

            def store_key(self, *_args, **_kwargs):
                return True

            def update_key_result(self, _key, _status, response_data=None):
                self.cached = {"status": "completed", "response_data": response_data}
                return True

        self.service._store_lead_in_db = _store
        data = {"formId": "f1", "submissionId": "s1", "createdAt": "now", "data": {
            "name": "Alice",
            "email": "a@b.com",
        }}

        with patch("core.webhook_intake_service.idempotency_manager", new=_Idem()):
            result1 = self.service.process_tally_webhook(data)
            result2 = self.service.process_tally_webhook(data)

        self.assertTrue(result1.get("success"))
        self.assertTrue(result2.get("success"))
        self.assertEqual(calls["count"], 1)

    def test_store_lead_in_db_failure(self):
        with patch("core.webhook_intake_service.db_optimizer") as mock_db:
            mock_db.execute_query.side_effect = Exception("db down")
            result = self.service._store_lead_in_db({
                "email": "a@b.com",
                "name": "A",
                "phone": "",
                "company": "",
                "source": "webhook",
                "status": "new",
                "score": 10,
                "notes": "",
                "tags": [],
                "metadata": {},
                "created_at": "now",
            })
        self.assertFalse(result.get("success"))
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
