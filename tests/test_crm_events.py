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
    def test_record_crm_event_legacy_schema_sets_tenant_user_id(self):
        import sqlite3
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            path = tmp.name
        conn = sqlite3.connect(path)
        conn.execute(
            """
            CREATE TABLE crm_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                occurred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                tenant_user_id INTEGER NOT NULL,
                actor_type TEXT NOT NULL DEFAULT 'user',
                event_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                correlation_id TEXT,
                supersedes_event_id INTEGER,
                payload_json TEXT,
                payload_truncated INTEGER NOT NULL DEFAULT 0,
                status TEXT,
                error_message TEXT,
                source TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER
            )
            """
        )
        conn.commit()
        conn.close()

        import crm.event_log as event_log_mod

        event_log_mod._schema_mode = None
        with patch("crm.event_log.db_optimizer") as mock_db:
            mock_db.list_table_columns.return_value = [
                "tenant_user_id",
                "user_id",
                "event_type",
                "entity_type",
                "entity_id",
                "occurred_at",
                "created_at",
                "actor_type",
            ]
            mock_db.execute_query = MagicMock()
            from crm.event_log import record_crm_event

            record_crm_event(108, "lead.created", "lead", 99, payload={"k": "v"})
            sql = mock_db.execute_query.call_args.args[0]
            params = mock_db.execute_query.call_args.args[1]
            self.assertIn("tenant_user_id", sql)
            self.assertEqual(params[0], 108)
            self.assertEqual(params[1], 108)

        os.unlink(path)

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
        import crm.event_log as event_log_mod

        event_log_mod._schema_mode = None
        with patch("crm.event_log.db_optimizer") as mock_db:
            mock_db.list_table_columns.return_value = [
                "user_id",
                "event_type",
                "entity_type",
                "entity_id",
                "created_at",
            ]
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
