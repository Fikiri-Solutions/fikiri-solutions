"""
Analytics coverage for triage, Command Center, and CRM hooks.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

os.environ["FIKIRI_SERVICE_USAGE_PERSIST_IN_TEST"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics.service_usage_recorders import (
    _safe_metadata,
    record_crm_lead_created,
    record_triage_classified,
    record_triage_reclassified,
)
from core.database_optimization import db_optimizer
from crm.service import EnhancedCRMService
from services.email_triage_service import (
    classify_unclassified_synced,
    execute_bulk_action,
    reclassify_synced_messages,
    triage_and_store_synced_message,
)


class ServiceUsageCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db_optimizer._initialize_database()

    def setUp(self):
        self.user_id = 1
        self._ensure_user(self.user_id)
        for uid in (self.user_id,):
            for table in (
                "service_usage_events",
                "service_daily_rollups",
                "tenant_service_metrics",
            ):
                if db_optimizer.table_exists(table):
                    db_optimizer.execute_query(
                        f"DELETE FROM {table} WHERE user_id = ?",
                        (uid,),
                        fetch=False,
                    )

    def _ensure_user(self, user_id: int) -> None:
        rows = db_optimizer.execute_query("SELECT id FROM users WHERE id = ?", (user_id,))
        if not rows:
            db_optimizer.execute_query(
                "INSERT INTO users (id, email, name, password_hash) VALUES (?, ?, ?, ?)",
                (user_id, f"coverage-{user_id}@example.test", f"T{user_id}", "hash"),
                fetch=False,
            )

    def _events(self, event_type: str | None = None):
        if event_type:
            rows = db_optimizer.execute_query(
                """
                SELECT event_type, metric_name, metadata_json, idempotency_key, quantity, status
                FROM service_usage_events
                WHERE user_id = ? AND event_type = ?
                ORDER BY id DESC
                """,
                (self.user_id, event_type),
            )
        else:
            rows = db_optimizer.execute_query(
                """
                SELECT event_type, metadata_json FROM service_usage_events
                WHERE user_id = ? ORDER BY id DESC
                """,
                (self.user_id,),
            )
        return [dict(r) for r in (rows or [])]

    @patch("services.email_triage_service.classify_email_triage")
    def test_triage_classification_records_service_event(self, mock_classify):
        mock_classify.return_value = {
            "category": "business_lead",
            "lead_score": 70,
            "cleanup_action": "keep",
            "confidence": 0.8,
            "reason": "test",
            "suggested_labels": [],
        }
        with patch("services.email_triage_service.mark_classified"):
            triage_and_store_synced_message(
                self.user_id,
                external_id="cov-msg-1",
                subject="Secret subject",
                body="Secret body content",
                sender_email="lead@example.test",
                provider="gmail",
            )
        rows = self._events("email_triage.classified")
        self.assertGreaterEqual(len(rows), 1)
        meta = json.loads(rows[0].get("metadata_json") or "{}")
        self.assertEqual(meta.get("category"), "business_lead")
        self.assertNotIn("body", meta)
        self.assertNotIn("subject", meta)
        blob = json.dumps(meta)
        self.assertNotIn("Secret body", blob)

    @patch("services.email_triage_service.triage_and_store_synced_message")
    @patch("services.email_triage_service.list_unclassified_synced")
    @patch("services.email_triage_service.should_classify_email", return_value=True)
    def test_classify_unclassified_records_aggregate(
        self, _mock_should, mock_list, mock_triage
    ):
        mock_list.return_value = [
            {
                "id": 1,
                "external_id": "u1",
                "provider": "gmail",
                "subject": "x",
                "body": "y",
                "sender": "a@b.com",
            }
        ]
        mock_triage.return_value = {"category": "other", "lead_score": 0}
        result = classify_unclassified_synced(self.user_id, limit=5)
        self.assertEqual(result["classified_count"], 1)
        rows = self._events("email_triage.classify_unclassified_completed")
        self.assertGreaterEqual(len(rows), 1)
        meta = json.loads(rows[0]["metadata_json"])
        self.assertEqual(meta.get("classified_count"), 1)
        self.assertEqual(meta.get("scanned"), 1)

    @patch("services.email_triage_service.classify_email_triage")
    def test_reclassify_records_force_true(self, mock_classify):
        mock_classify.return_value = {
            "category": "newsletter",
            "lead_score": 0,
            "cleanup_action": "archive",
            "confidence": 0.9,
            "reason": "r",
            "suggested_labels": [],
        }
        db_optimizer.execute_query(
            """
            INSERT OR REPLACE INTO synced_emails (
                user_id, gmail_id, external_id, provider, subject, sender, body, date, processed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), 0)
            """,
            (
                self.user_id,
                "re-1",
                "re-1",
                "gmail",
                "hidden subject",
                "x@y.com",
                "hidden body",
            ),
            fetch=False,
        )
        with patch("services.email_triage_service.mark_reclassified"):
            with patch("core.email_triage_store.upsert_classification"):
                reclassify_synced_messages(self.user_id, ["re-1"])
        rows = self._events("email_triage.reclassified")
        self.assertGreaterEqual(len(rows), 1)
        meta = json.loads(rows[0]["metadata_json"])
        self.assertTrue(meta.get("force"))
        self.assertNotIn("hidden body", json.dumps(meta))

    @patch("integrations.gmail.gmail_client.gmail_client")
    def test_bulk_action_records_action_and_count(self, mock_gmail):
        service = MagicMock()
        mock_gmail.get_gmail_service_for_user.return_value = service
        service.users.return_value.messages.return_value.modify.return_value.execute.return_value = {}
        execute_bulk_action(self.user_id, action="archive", email_ids=["m1", "m2"])
        archive_rows = self._events("command_center.archive")
        bulk_rows = self._events("email_triage.bulk_action_applied")
        self.assertGreaterEqual(len(archive_rows), 1)
        self.assertGreaterEqual(len(bulk_rows), 1)
        meta = json.loads(bulk_rows[0]["metadata_json"])
        self.assertEqual(meta.get("action"), "archive")
        self.assertGreaterEqual(meta.get("processed_count"), 1)

    @patch("crm.service.record_crm_event")
    @patch("crm.service.db_optimizer")
    def test_crm_create_lead_records_event(self, mock_db, _mock_crm_event):
        mock_db.execute_query.side_effect = [
            [],
            None,
            [{"id": 501}],
        ]
        mock_db.execute_insert_returning_id.return_value = 1
        svc = EnhancedCRMService()
        with patch.object(svc, "_add_lead_activity"), patch(
            "services.automation_engine.automation_engine.execute_automation_rules"
        ):
            result = svc.create_lead(
                self.user_id,
                {"email": "newlead@example.test", "name": "New Lead", "phone": "555"},
            )
        self.assertTrue(result.get("success"))
        rows = self._events("crm.lead_created")
        self.assertGreaterEqual(len(rows), 1)
        meta = json.loads(rows[0]["metadata_json"])
        self.assertEqual(meta.get("lead_id"), 501)
        self.assertTrue(meta.get("has_email"))
        self.assertTrue(meta.get("has_phone"))
        self.assertNotIn("newlead@example.test", json.dumps(meta))

    @patch("crm.service.record_crm_event")
    @patch("crm.service.db_optimizer")
    def test_crm_stage_change_records_event(self, mock_db, _mock_crm_event):
        row = {
            "id": 10,
            "user_id": self.user_id,
            "email": "stage@example.test",
            "name": "Stage",
            "phone": None,
            "company": None,
            "source": "manual",
            "stage": "new",
            "score": 0,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-01",
            "last_contact": None,
            "notes": None,
            "tags": "[]",
            "metadata": "{}",
        }
        updated = dict(row)
        updated["stage"] = "qualified"
        mock_db.execute_query.side_effect = [
            [dict(row)],
            None,
            [updated],
            None,
        ]
        svc = EnhancedCRMService()
        svc._get_lead_activity_metrics = lambda _id: (0, None)
        svc._score_lead_data = lambda *_a, **_k: {"score": 10, "quality": "C", "breakdown": {}}
        with patch.object(svc, "_add_lead_activity"), patch(
            "services.automation_engine.automation_engine.execute_automation_rules"
        ):
            result = svc.update_lead(10, self.user_id, {"stage": "qualified"})
        self.assertTrue(result.get("success"))
        stage_rows = self._events("crm.lead_stage_changed")
        self.assertGreaterEqual(len(stage_rows), 1)
        meta = json.loads(stage_rows[0]["metadata_json"])
        self.assertEqual(meta.get("previous_stage"), "new")
        self.assertEqual(meta.get("new_stage"), "qualified")
        converted = self._events("crm.lead_converted")
        self.assertGreaterEqual(len(converted), 1)

    @patch("analytics.service_usage_recorders.record_service_usage_event", side_effect=RuntimeError("db down"))
    @patch("services.email_triage_service.classify_email_triage")
    def test_analytics_failure_does_not_break_triage(self, mock_classify, _mock_record):
        mock_classify.return_value = {
            "category": "other",
            "lead_score": 0,
            "cleanup_action": "keep",
            "confidence": 0.5,
            "reason": "x",
            "suggested_labels": [],
        }
        with patch("services.email_triage_service.mark_classified"):
            triage = triage_and_store_synced_message(
                self.user_id,
                external_id="fail-open-1",
                subject="s",
                body="b",
                sender_email="a@b.com",
            )
        self.assertIn("category", triage)

    def test_safe_metadata_strips_pii(self):
        meta = _safe_metadata(
            {
                "category": "lead",
                "email": "secret@example.com",
                "body": "long body",
                "query": "user question",
                "count": 3,
                "force": True,
            }
        )
        self.assertEqual(meta.get("category"), "lead")
        self.assertEqual(meta.get("count"), 3)
        self.assertNotIn("email", meta)
        self.assertNotIn("body", meta)
        self.assertNotIn("query", meta)

    def test_idempotent_reclassify_per_message(self):
        record_triage_reclassified(
            self.user_id,
            external_id="idem-re",
            category="spam",
            force=True,
        )
        record_triage_reclassified(
            self.user_id,
            external_id="idem-re",
            category="spam",
            force=True,
        )
        rows = db_optimizer.execute_query(
            """
            SELECT COUNT(*) AS c FROM service_usage_events
            WHERE user_id = ? AND event_type = 'email_triage.reclassified'
              AND resource_id = 'idem-re'
            """,
            (self.user_id,),
        )
        self.assertEqual(int(rows[0]["c"]), 1)

    def test_record_helpers_direct(self):
        record_triage_classified(self.user_id, external_id="direct-1", category="other", source="manual")
        record_crm_lead_created(
            self.user_id,
            lead_id=99,
            source="manual",
            has_email=True,
            has_phone=False,
        )
        self.assertGreaterEqual(len(self._events()), 2)


if __name__ == "__main__":
    unittest.main()
