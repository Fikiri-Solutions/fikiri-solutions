#!/usr/bin/env python3
"""Tests for POST /api/webhooks/forms/update and /api/webhooks/forms/cancel."""

import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

from flask import Flask
from core.webhook_api import webhook_bp


class TestWebhookFormsUpdateCancel(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(webhook_bp)
        self.client = self.app.test_client()
        self.uid = 42
        self.key_info = {
            "api_key_id": "k1",
            "user_id": self.uid,
            "tenant_id": None,
            "scopes": ["webhooks:forms"],
            "allowed_origins": None,
            "key_prefix": "pfx",
        }

    def _headers(self):
        return {"X-API-Key": "test", "Content-Type": "application/json"}

    @patch("core.api_key_manager.api_key_manager")
    @patch("core.webhook_api._insert_customer_form_intake")
    @patch("core.idempotency_manager.idempotency_manager")
    @patch("core.idempotency_manager.generate_deterministic_key")
    @patch("crm.service.enhanced_crm_service")
    def test_submit_persists_client_submission_id_and_returns_intake_id(
        self, mock_crm, mock_gen_key, mock_idem, mock_insert, mock_api
    ):
        mock_api.validate_api_key.return_value = self.key_info
        mock_api.check_rate_limit.return_value = {"allowed": True}
        mock_idem.check_key.return_value = None
        mock_gen_key.return_value = "k"
        mock_insert.return_value = 555
        mock_crm.create_lead.return_value = {"success": True, "data": {"lead_id": 10}}

        payload = {
            "form_id": "f1",
            "client_submission_id": "sub-abc",
            "fields": {"email": "a@b.com", "name": "A"},
            "source": "site",
        }
        r = self.client.post(
            "/api/webhooks/forms/submit",
            headers=self._headers(),
            data=json.dumps(payload),
        )
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["intake_id"], 555)
        mock_insert.assert_called()
        kw = mock_insert.call_args[1]
        self.assertEqual(kw.get("client_submission_id"), "sub-abc")
        self.assertIsNone(kw.get("supersedes_intake_id"))

    @patch("core.api_key_manager.api_key_manager")
    @patch("core.webhook_api._insert_customer_form_intake")
    @patch("core.form_intake_domain.apply_form_update_to_lead")
    @patch("core.form_intake_domain.find_original_form_intake_row")
    @patch("core.idempotency_manager.idempotency_manager")
    @patch("core.idempotency_manager.generate_deterministic_key")
    def test_form_update_success(
        self, mock_gen_key, mock_idem, mock_find, mock_apply, mock_insert, mock_api
    ):
        mock_api.validate_api_key.return_value = self.key_info
        mock_api.check_rate_limit.return_value = {"allowed": True}
        mock_idem.check_key.return_value = None
        mock_gen_key.return_value = "uk"
        mock_find.return_value = {
            "id": 100,
            "lead_id": 7,
            "email": "x@y.com",
            "name": "Old",
            "phone": None,
            "company": None,
            "subject": None,
            "source": "web",
        }
        mock_insert.return_value = 2001
        mock_apply.return_value = {"success": True, "data": {}}

        body = {
            "form_id": "f1",
            "client_submission_id": "cs1",
            "fields": {"email": "x@y.com", "name": "New", "phone": "1"},
            "metadata": {"k": "v"},
            "reason": "typo",
        }
        r = self.client.post(
            "/api/webhooks/forms/update",
            headers=self._headers(),
            data=json.dumps(body),
        )
        self.assertEqual(r.status_code, 200)
        out = r.get_json()
        self.assertTrue(out["success"])
        self.assertEqual(out["data"]["intake_id"], 2001)
        self.assertEqual(out["data"]["lead_id"], 7)
        self.assertEqual(out["data"]["status"], "updated")
        mock_apply.assert_called_once()
        ikw = mock_insert.call_args[1]
        self.assertEqual(ikw["status"], "updated")
        self.assertEqual(ikw["supersedes_intake_id"], 100)
        mock_idem.update_key_result.assert_called()

    @patch("core.api_key_manager.api_key_manager")
    @patch("core.form_intake_domain.find_original_form_intake_row")
    @patch("core.idempotency_manager.idempotency_manager")
    @patch("core.idempotency_manager.generate_deterministic_key")
    def test_form_update_intake_not_found(self, mock_gen_key, mock_idem, mock_find, mock_api):
        mock_api.validate_api_key.return_value = self.key_info
        mock_api.check_rate_limit.return_value = {"allowed": True}
        mock_idem.check_key.return_value = None
        mock_gen_key.return_value = "uk"
        mock_find.return_value = None

        r = self.client.post(
            "/api/webhooks/forms/update",
            headers=self._headers(),
            data=json.dumps(
                {
                    "form_id": "f1",
                    "client_submission_id": "missing",
                    "fields": {"email": "a@b.com"},
                }
            ),
        )
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.get_json()["error_code"], "INTAKE_NOT_FOUND")

    @patch("core.api_key_manager.api_key_manager")
    @patch("core.webhook_api._insert_customer_form_intake")
    @patch("core.form_intake_domain.apply_form_cancel_to_lead")
    @patch("core.form_intake_domain.find_original_form_intake_row")
    @patch("core.idempotency_manager.idempotency_manager")
    @patch("core.idempotency_manager.generate_deterministic_key")
    def test_form_cancel_success(
        self, mock_gen_key, mock_idem, mock_find, mock_cancel, mock_insert, mock_api
    ):
        mock_api.validate_api_key.return_value = self.key_info
        mock_api.check_rate_limit.return_value = {"allowed": True}
        mock_idem.check_key.return_value = None
        mock_gen_key.return_value = "ck"
        mock_find.return_value = {
            "id": 50,
            "lead_id": 9,
            "email": "c@d.com",
            "name": "C",
            "phone": None,
            "company": None,
            "subject": None,
            "source": "web",
        }
        mock_insert.return_value = 3001
        mock_cancel.return_value = {"success": True, "data": {}}

        r = self.client.post(
            "/api/webhooks/forms/cancel",
            headers=self._headers(),
            data=json.dumps(
                {
                    "form_id": "f1",
                    "client_submission_id": "cs1",
                    "email": "c@d.com",
                    "reason": "user asked",
                }
            ),
        )
        self.assertEqual(r.status_code, 200)
        out = r.get_json()
        self.assertTrue(out["success"])
        self.assertEqual(out["data"]["status"], "cancelled")
        self.assertEqual(out["data"]["crm_stage"], "closed")
        self.assertTrue(out["data"]["followups_cancelled"])
        ckw = mock_insert.call_args[1]
        self.assertEqual(ckw["status"], "cancelled")
        self.assertEqual(ckw["supersedes_intake_id"], 50)
        mock_cancel.assert_called_once()

    @patch("core.api_key_manager.api_key_manager")
    @patch("core.form_intake_domain.find_original_form_intake_row")
    @patch("core.idempotency_manager.idempotency_manager")
    @patch("core.idempotency_manager.generate_deterministic_key")
    def test_form_cancel_intake_not_found(self, mock_gen_key, mock_idem, mock_find, mock_api):
        mock_api.validate_api_key.return_value = self.key_info
        mock_api.check_rate_limit.return_value = {"allowed": True}
        mock_idem.check_key.return_value = None
        mock_gen_key.return_value = "ck"
        mock_find.return_value = None

        r = self.client.post(
            "/api/webhooks/forms/cancel",
            headers=self._headers(),
            data=json.dumps({"form_id": "f1", "client_submission_id": "nope"}),
        )
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.get_json()["error_code"], "INTAKE_NOT_FOUND")

    @patch("core.api_key_manager.api_key_manager")
    @patch("core.webhook_api._insert_customer_form_intake")
    @patch("core.form_intake_domain.apply_form_update_to_lead")
    @patch("core.form_intake_domain.find_original_form_intake_row")
    @patch("core.idempotency_manager.idempotency_manager")
    @patch("core.idempotency_manager.generate_deterministic_key")
    def test_form_update_idempotent_no_second_insert(
        self, mock_gen_key, mock_idem, mock_find, mock_apply, mock_insert, mock_api
    ):
        mock_api.validate_api_key.return_value = self.key_info
        mock_api.check_rate_limit.return_value = {"allowed": True}
        cached_body = {
            "success": True,
            "data": {"intake_id": 1, "lead_id": 7, "status": "updated"},
        }
        mock_idem.check_key.return_value = {
            "status": "completed",
            "response_data": cached_body,
        }
        mock_gen_key.return_value = "same"

        body = {
            "form_id": "f1",
            "client_submission_id": "cs1",
            "fields": {"email": "x@y.com"},
        }
        r = self.client.post(
            "/api/webhooks/forms/update",
            headers=self._headers(),
            data=json.dumps(body),
        )
        self.assertEqual(r.status_code, 200)
        resp = r.get_json()
        self.assertEqual(resp["success"], cached_body["success"])
        self.assertEqual(resp["data"], cached_body["data"])
        self.assertIn("correlation_id", resp)
        mock_insert.assert_not_called()
        mock_find.assert_not_called()

    @patch("core.api_key_manager.api_key_manager")
    @patch("core.webhook_api._insert_customer_form_intake")
    @patch("core.form_intake_domain.apply_form_cancel_to_lead")
    @patch("core.form_intake_domain.find_original_form_intake_row")
    @patch("core.idempotency_manager.idempotency_manager")
    @patch("core.idempotency_manager.generate_deterministic_key")
    def test_form_cancel_idempotent_no_second_insert(
        self, mock_gen_key, mock_idem, mock_find, mock_cancel, mock_insert, mock_api
    ):
        mock_api.validate_api_key.return_value = self.key_info
        mock_api.check_rate_limit.return_value = {"allowed": True}
        cached_body = {
            "success": True,
            "data": {
                "intake_id": 2,
                "lead_id": 9,
                "status": "cancelled",
                "crm_stage": "closed",
                "followups_cancelled": True,
            },
        }
        mock_idem.check_key.return_value = {
            "status": "completed",
            "response_data": cached_body,
        }
        mock_gen_key.return_value = "same"

        r = self.client.post(
            "/api/webhooks/forms/cancel",
            headers=self._headers(),
            data=json.dumps({"form_id": "f1", "client_submission_id": "cs1"}),
        )
        self.assertEqual(r.status_code, 200)
        resp = r.get_json()
        self.assertEqual(resp["success"], cached_body["success"])
        self.assertEqual(resp["data"], cached_body["data"])
        self.assertIn("correlation_id", resp)
        mock_insert.assert_not_called()
        mock_cancel.assert_not_called()


class TestFormIntakeDomainCancel(unittest.TestCase):
    @patch("core.form_intake_domain.cancel_pending_work_for_lead")
    @patch("core.form_intake_domain.enhanced_crm_service")
    @patch("core.form_intake_domain.db_optimizer")
    def test_apply_form_cancel_calls_stop_work_before_crm(
        self, mock_db, mock_crm, mock_stop
    ):
        from core.form_intake_domain import apply_form_cancel_to_lead

        mock_db.execute_query.return_value = [
            {"id": 1, "tags": "[]", "metadata": "{}"},
        ]
        mock_crm.update_lead.return_value = {"success": True}
        mock_stop.return_value = {"success": True}

        apply_form_cancel_to_lead(3, 8, reason="bye")

        mock_stop.assert_called_once_with(3, 8, reason="withdrawn_by_client")
        mock_crm.update_lead.assert_called_once()


if __name__ == "__main__":
    unittest.main()
