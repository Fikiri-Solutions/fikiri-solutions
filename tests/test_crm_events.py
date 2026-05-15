#!/usr/bin/env python3
"""CRM append-only event log (crm_events) tests."""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


class TestCRMEventLog(unittest.TestCase):
    def test_record_crm_event_swallows_db_errors(self):
        with patch("crm.event_log.db_optimizer") as mock_db:
            mock_db.execute_query.side_effect = RuntimeError("db down")
            from crm.event_log import record_crm_event

            record_crm_event(
                user_id=1,
                event_type="lead.created",
                entity_type="lead",
                entity_id=42,
                payload={"ok": True},
            )

    def test_record_crm_event_truncates_large_payload(self):
        with patch("crm.event_log.db_optimizer") as mock_db:
            mock_db.execute_query = MagicMock()
            from crm.event_log import record_crm_event

            huge = {"x": "y" * 50000}
            record_crm_event(1, "lead.updated", "lead", 1, huge)
            self.assertTrue(mock_db.execute_query.called)
            params = mock_db.execute_query.call_args.args[1]
            self.assertEqual(params[7], 1)


class TestCompletionAPIStageUpdate(unittest.TestCase):
    def setUp(self):
        from flask import Flask
        from crm.completion_api import crm_bp

        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(crm_bp)
        self.client = self.app.test_client()

    @patch("core.jwt_auth.get_jwt_manager")
    def test_stage_update_requires_auth(self, mock_mgr):
        mock_mgr.return_value.verify_access_token.return_value = {"error": "invalid"}
        response = self.client.put(
            "/api/crm/pipeline/leads/1/stage",
            json={"stage": "contacted"},
            content_type="application/json",
            headers={"Authorization": "Bearer x"},
        )
        self.assertEqual(response.status_code, 401)

    @patch("core.jwt_auth.get_jwt_manager")
    @patch("crm.completion_api.enhanced_crm_service")
    def test_stage_update_delegates_to_service(self, mock_svc, mock_mgr):
        mock_mgr.return_value.verify_access_token.return_value = {
            "user_id": 7,
            "type": "access",
            "role": "user",
        }
        from crm.service import Lead
        from datetime import datetime

        mock_svc.update_lead.return_value = {
            "success": True,
            "data": {
                "lead": Lead(
                    id=1,
                    user_id=7,
                    email="a@b.com",
                    name="A",
                    phone=None,
                    company=None,
                    source="manual",
                    stage="contacted",
                    score=10,
                    created_at=datetime(2024, 1, 1),
                    updated_at=datetime(2024, 1, 2),
                    last_contact=None,
                    notes=None,
                    tags=[],
                    metadata={},
                ),
                "message": "ok",
            },
        }
        response = self.client.put(
            "/api/crm/pipeline/leads/1/stage",
            json={"stage": "contacted"},
            content_type="application/json",
            headers={"Authorization": "Bearer t"},
        )
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.data)
        self.assertTrue(body.get("success"))
        mock_svc.update_lead.assert_called_once_with(1, 7, {"stage": "contacted"})


if __name__ == "__main__":
    unittest.main()
