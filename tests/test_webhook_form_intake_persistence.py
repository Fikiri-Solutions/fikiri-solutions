#!/usr/bin/env python3
"""Tests persistence for webhook form intake submissions."""

import unittest
import json
from unittest.mock import patch, MagicMock
import os
import sys
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.webhook_api import webhook_bp


class TestWebhookFormIntakePersistence(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(webhook_bp)
        self.client = self.app.test_client()

    @patch("crm.service.enhanced_crm_service")
    @patch("core.idempotency_manager.generate_deterministic_key")
    @patch("core.idempotency_manager.idempotency_manager")
    @patch("core.api_key_manager.api_key_manager")
    @patch("core.webhook_api.db_optimizer")
    def test_forms_submit_completed_inserts_submission(
        self,
        mock_db,
        mock_api_key_mgr,
        mock_idem_mgr,
        mock_gen_key,
        mock_crm_service,
    ):
        mock_gen_key.return_value = "fixed-idem-key"
        mock_idem_mgr.check_key.return_value = None
        mock_idem_mgr.update_key_result.return_value = None
        mock_idem_mgr.store_key.return_value = None

        mock_api_key_mgr.validate_api_key.return_value = {
            "api_key_id": "kid1",
            "user_id": 1,
            "tenant_id": None,
            "scopes": ["webhooks:forms"],
            "allowed_origins": None,
            "key_prefix": "kprefix",
        }
        mock_api_key_mgr.check_rate_limit.return_value = {"allowed": True}
        mock_api_key_mgr.record_usage.return_value = None

        def _db_exec(query, params=None, fetch=True, **kwargs):
            if fetch and query and "last_insert_rowid" in query.lower():
                return [{"id": 9001}]
            return 1 if not fetch else []

        mock_db.execute_query.side_effect = _db_exec

        mock_crm_service.create_lead.return_value = {"success": True, "data": {"lead_id": "L42"}}

        payload = {
            "form_id": "test-form",
            "fields": {
                "email": "jane@example.com",
                "name": "Jane",
                "phone": "+15550001111",
            },
            "source": "website",
            "metadata": {"any": "thing"},
        }

        response = self.client.post(
            "/api/webhooks/forms/submit",
            headers={"X-API-Key": "k", "Content-Type": "application/json"},
            data=json.dumps(payload),
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("lead_id"), "L42")
        self.assertEqual((data.get("data") or {}).get("intake_id"), 9001)

        # Ensure we inserted into our intake persistence table.
        insert_calls = [c for c in mock_db.execute_query.call_args_list if "customer_form_intake_submissions" in c[0][0]]
        self.assertTrue(len(insert_calls) >= 1)

    @patch("crm.service.enhanced_crm_service")
    @patch("core.idempotency_manager.generate_deterministic_key")
    @patch("core.idempotency_manager.idempotency_manager")
    @patch("core.api_key_manager.api_key_manager")
    @patch("core.webhook_api.db_optimizer")
    def test_forms_submit_failed_create_lead_inserts_failed(
        self,
        mock_db,
        mock_api_key_mgr,
        mock_idem_mgr,
        mock_gen_key,
        mock_crm_service,
    ):
        mock_gen_key.return_value = "fixed-idem-key"
        mock_idem_mgr.check_key.return_value = None
        mock_idem_mgr.update_key_result.return_value = None
        mock_idem_mgr.store_key.return_value = None

        mock_api_key_mgr.validate_api_key.return_value = {
            "api_key_id": "kid1",
            "user_id": 1,
            "tenant_id": None,
            "scopes": ["webhooks:forms"],
            "allowed_origins": None,
            "key_prefix": "kprefix",
        }
        mock_api_key_mgr.check_rate_limit.return_value = {"allowed": True}
        mock_api_key_mgr.record_usage.return_value = None

        def _db_exec2(query, params=None, fetch=True, **kwargs):
            if fetch and query and "last_insert_rowid" in query.lower():
                return [{"id": 9002}]
            return 1 if not fetch else []

        mock_db.execute_query.side_effect = _db_exec2

        mock_crm_service.create_lead.return_value = {"success": False, "error": "lead create failed", "error_code": "LEAD_CREATE_FAILED"}

        payload = {
            "form_id": "test-form",
            "fields": {"email": "jane@example.com", "name": "Jane"},
            "source": "website",
            "metadata": {},
        }

        response = self.client.post(
            "/api/webhooks/forms/submit",
            headers={"X-API-Key": "k", "Content-Type": "application/json"},
            data=json.dumps(payload),
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data.get("success"))

        insert_calls = [c for c in mock_db.execute_query.call_args_list if "customer_form_intake_submissions" in c[0][0]]
        self.assertTrue(len(insert_calls) >= 1)


if __name__ == "__main__":
    unittest.main()

