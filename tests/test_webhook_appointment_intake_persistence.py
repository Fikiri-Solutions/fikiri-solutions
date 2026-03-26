#!/usr/bin/env python3
"""Tests persistence for public appointment intake endpoint."""

import unittest
import json
from unittest.mock import patch
import os
import sys
from flask import Flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.webhook_api import webhook_bp


class TestWebhookAppointmentIntakePersistence(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(webhook_bp)
        self.client = self.app.test_client()

    @patch("core.webhook_api.AppointmentsService")
    @patch("core.webhook_api.db_optimizer")
    @patch("core.api_key_manager.api_key_manager")
    @patch("core.idempotency_manager.idempotency_manager")
    @patch("core.idempotency_manager.generate_deterministic_key")
    def test_book_persists_completed(
        self,
        mock_gen_key,
        mock_idem_mgr,
        mock_api_key_mgr,
        mock_db,
        mock_appointments_service,
    ):
        mock_gen_key.return_value = "fixed-idem-key"
        mock_idem_mgr.check_key.return_value = None
        mock_idem_mgr.store_key.return_value = None
        mock_idem_mgr.update_key_result.return_value = None

        mock_api_key_mgr.validate_api_key.return_value = {
            "api_key_id": "kid1",
            "user_id": 1,
            "tenant_id": None,
            "scopes": ["webhooks:*"],
            "allowed_origins": None,
            "key_prefix": "kprefix",
        }
        mock_api_key_mgr.check_rate_limit.return_value = {"allowed": True}
        mock_api_key_mgr.record_usage.return_value = None

        mock_appointments_service.return_value.create_appointment.return_value = {
            "id": 10,
            "contact_name": "Jane",
            "contact_email": "jane@example.com",
            "contact_phone": "+15550001111",
            "title": "Consultation",
        }

        payload = {
            "action": "book",
            "service_type": "Consultation",
            "start_time": "2026-03-19T10:00:00Z",
            "end_time": "2026-03-19T10:30:00Z",
            "timezone": "UTC",
            "customer_name": "Jane",
            "customer_email": "jane@example.com",
            "customer_phone": "+15550001111",
        }

        response = self.client.post(
            "/api/webhooks/appointments/submit",
            headers={"X-API-Key": "k", "Content-Type": "application/json", "User-Agent": "jest"},
            data=json.dumps(payload),
        )

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.data)
        self.assertTrue(body.get("success"))
        self.assertEqual(body.get("appointment_id"), 10)

        insert_calls = [
            c for c in mock_db.execute_query.call_args_list
            if "customer_appointment_intake_submissions" in (c[0][0] or "")
        ]
        self.assertTrue(len(insert_calls) >= 1)
        # status is passed as a parameter; verify it became "completed"
        flat_params = list(insert_calls[0][0][1] or [])
        self.assertIn("completed", flat_params)
        self.assertIn(10, flat_params)

    @patch("core.webhook_api.AppointmentsService")
    @patch("core.webhook_api.db_optimizer")
    @patch("core.api_key_manager.api_key_manager")
    @patch("core.idempotency_manager.idempotency_manager")
    @patch("core.idempotency_manager.generate_deterministic_key")
    def test_cancel_persists_cancelled(
        self,
        mock_gen_key,
        mock_idem_mgr,
        mock_api_key_mgr,
        mock_db,
        mock_appointments_service,
    ):
        mock_gen_key.return_value = "fixed-idem-key"
        mock_idem_mgr.check_key.return_value = None
        mock_idem_mgr.store_key.return_value = None
        mock_idem_mgr.update_key_result.return_value = None

        mock_api_key_mgr.validate_api_key.return_value = {
            "api_key_id": "kid1",
            "user_id": 1,
            "tenant_id": None,
            "scopes": ["webhooks:*"],
            "allowed_origins": None,
            "key_prefix": "kprefix",
        }
        mock_api_key_mgr.check_rate_limit.return_value = {"allowed": True}
        mock_api_key_mgr.record_usage.return_value = None

        mock_appointments_service.return_value.cancel_appointment.return_value = {
            "id": 10,
            "contact_name": "Jane",
            "contact_email": "jane@example.com",
            "contact_phone": "+15550001111",
            "title": "Consultation",
        }

        payload = {
            "action": "cancel",
            "appointment_id": 10,
            "service_type": "Consultation",
        }

        response = self.client.post(
            "/api/webhooks/appointments/submit",
            headers={"X-API-Key": "k", "Content-Type": "application/json", "User-Agent": "jest"},
            data=json.dumps(payload),
        )

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.data)
        self.assertTrue(body.get("success"))
        self.assertEqual(body.get("appointment_id"), 10)

        insert_calls = [
            c for c in mock_db.execute_query.call_args_list
            if "customer_appointment_intake_submissions" in (c[0][0] or "")
        ]
        self.assertTrue(len(insert_calls) >= 1)
        flat_params = list(insert_calls[0][0][1] or [])
        self.assertIn("cancelled", flat_params)
        self.assertIn(10, flat_params)

    @patch("core.webhook_api.AppointmentsService")
    @patch("core.webhook_api.db_optimizer")
    @patch("core.api_key_manager.api_key_manager")
    @patch("core.idempotency_manager.idempotency_manager")
    @patch("core.idempotency_manager.generate_deterministic_key")
    def test_cancel_endpoint_persists_cancelled(
        self,
        mock_gen_key,
        mock_idem_mgr,
        mock_api_key_mgr,
        mock_db,
        mock_appointments_service,
    ):
        mock_gen_key.return_value = "fixed-idem-key"
        mock_idem_mgr.check_key.return_value = None
        mock_idem_mgr.store_key.return_value = None
        mock_idem_mgr.update_key_result.return_value = None

        mock_api_key_mgr.validate_api_key.return_value = {
            "api_key_id": "kid1",
            "user_id": 1,
            "tenant_id": None,
            "scopes": ["webhooks:*"],
            "allowed_origins": None,
            "key_prefix": "kprefix",
        }
        mock_api_key_mgr.check_rate_limit.return_value = {"allowed": True}
        mock_api_key_mgr.record_usage.return_value = None

        mock_appointments_service.return_value.cancel_appointment.return_value = {
            "id": 10,
            "contact_name": "Jane",
            "contact_email": "jane@example.com",
            "contact_phone": "+15550001111",
            "title": "Consultation",
        }

        payload = {
            "appointment_id": 10,
            "service_type": "Consultation",
        }

        response = self.client.post(
            "/api/webhooks/appointments/cancel",
            headers={"X-API-Key": "k", "Content-Type": "application/json", "User-Agent": "jest"},
            data=json.dumps(payload),
        )

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.data)
        self.assertTrue(body.get("success"))
        self.assertEqual(body.get("appointment_id"), 10)

        insert_calls = [
            c
            for c in mock_db.execute_query.call_args_list
            if "customer_appointment_intake_submissions" in (c[0][0] or "")
        ]
        self.assertTrue(len(insert_calls) >= 1)
        flat_params = list(insert_calls[0][0][1] or [])
        self.assertIn("cancelled", flat_params)
        self.assertIn(10, flat_params)

    @patch("core.webhook_api.AppointmentsService")
    @patch("core.webhook_api.db_optimizer")
    @patch("core.api_key_manager.api_key_manager")
    @patch("core.idempotency_manager.idempotency_manager")
    @patch("core.idempotency_manager.generate_deterministic_key")
    def test_reschedule_endpoint_persists_rescheduled(
        self,
        mock_gen_key,
        mock_idem_mgr,
        mock_api_key_mgr,
        mock_db,
        mock_appointments_service,
    ):
        mock_gen_key.return_value = "fixed-idem-key"
        mock_idem_mgr.check_key.return_value = None
        mock_idem_mgr.store_key.return_value = None
        mock_idem_mgr.update_key_result.return_value = None

        mock_api_key_mgr.validate_api_key.return_value = {
            "api_key_id": "kid1",
            "user_id": 1,
            "tenant_id": None,
            "scopes": ["webhooks:*"],
            "allowed_origins": None,
            "key_prefix": "kprefix",
        }
        mock_api_key_mgr.check_rate_limit.return_value = {"allowed": True}
        mock_api_key_mgr.record_usage.return_value = None

        mock_appointments_service.return_value.update_appointment.return_value = {
            "id": 10,
        }

        payload = {
            "appointment_id": 10,
            "start_time": "2026-03-19T11:00:00Z",
            "end_time": "2026-03-19T11:30:00Z",
        }

        response = self.client.post(
            "/api/webhooks/appointments/reschedule",
            headers={"X-API-Key": "k", "Content-Type": "application/json", "User-Agent": "jest"},
            data=json.dumps(payload),
        )

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.data)
        self.assertTrue(body.get("success"))
        self.assertEqual(body.get("appointment_id"), 10)

        insert_calls = [
            c
            for c in mock_db.execute_query.call_args_list
            if "customer_appointment_intake_submissions" in (c[0][0] or "")
        ]
        self.assertTrue(len(insert_calls) >= 1)
        flat_params = list(insert_calls[0][0][1] or [])
        self.assertIn("rescheduled", flat_params)
        self.assertIn(10, flat_params)


if __name__ == "__main__":
    unittest.main()

