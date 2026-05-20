"""
Regression tests for unified service usage analytics layer.
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ["FIKIRI_SERVICE_USAGE_PERSIST_IN_TEST"] = "1"

from analytics.service_usage_analytics import (
    build_idempotency_key,
    get_tenant_service_summary,
    mirror_billing_usage_to_analytics,
    record_ai_service_usage,
    record_automation_service_usage,
    record_service_usage_event,
)
from analytics.service_activity_rollups import rebuild_daily_rollups_for_user, refresh_tenant_analytics
from analytics.service_health_metrics import get_automation_health, get_tenant_health_snapshot
from core.database_optimization import db_optimizer


class ServiceUsageAnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db_optimizer._initialize_database()

    def _ensure_user(self, user_id: int) -> None:
        existing = db_optimizer.execute_query(
            "SELECT id FROM users WHERE id = ?", (user_id,)
        )
        if not existing:
            db_optimizer.execute_query(
                "INSERT INTO users (id, email, name, password_hash) VALUES (?, ?, ?, ?)",
                (user_id, f"analytics-test-{user_id}@example.test", f"Test {user_id}", "hash"),
                fetch=False,
            )

    def setUp(self):
        if not db_optimizer.table_exists("service_usage_events"):
            db_optimizer._initialize_database()
        self._user_a = 1
        self._user_b = 2
        self._ensure_user(self._user_a)
        self._ensure_user(self._user_b)
        for uid in (self._user_a, self._user_b):
            db_optimizer.execute_query(
                "DELETE FROM service_usage_events WHERE user_id = ?",
                (uid,),
                fetch=False,
            )
            db_optimizer.execute_query(
                "DELETE FROM service_daily_rollups WHERE user_id = ?",
                (uid,),
                fetch=False,
            )
            db_optimizer.execute_query(
                "DELETE FROM tenant_service_metrics WHERE user_id = ?",
                (uid,),
                fetch=False,
            )

    def test_idempotent_event_not_double_counted(self):
        key = build_idempotency_key("test", self._user_a, "chatbot", "corr-1")
        first = record_service_usage_event(
            user_id=self._user_a,
            service_id="chatbot",
            event_type="ai_call",
            metric_name="ai_responses",
            idempotency_key=key,
            quantity=1.0,
        )
        second = record_service_usage_event(
            user_id=self._user_a,
            service_id="chatbot",
            event_type="ai_call",
            metric_name="ai_responses",
            idempotency_key=key,
            quantity=1.0,
        )
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        rows = db_optimizer.execute_query(
            "SELECT COUNT(*) AS c FROM service_usage_events WHERE user_id = ? AND idempotency_key = ?",
            (self._user_a, key),
        )
        self.assertEqual(int(rows[0]["c"]), 1)

    def test_tenant_metrics_isolated(self):
        """Events for tenant A must not appear in tenant B queries."""
        record_ai_service_usage(self._user_a, "chatbot", correlation_id="a1")
        record_ai_service_usage(self._user_b, "chatbot", correlation_id="b1")
        rows_b = db_optimizer.execute_query(
            "SELECT COUNT(*) AS c FROM service_usage_events WHERE user_id = ?",
            (self._user_b,),
        )
        self.assertGreaterEqual(int(rows_b[0]["c"]), 1)
        cross = db_optimizer.execute_query(
            """
            SELECT COUNT(*) AS c FROM service_usage_events
            WHERE user_id = ? AND idempotency_key LIKE '%a1%'
            """,
            (self._user_b,),
        )
        self.assertEqual(int(cross[0]["c"]), 0)

    def test_ai_usage_attribution_by_service(self):
        record_ai_service_usage(self._user_a, "chatbot", correlation_id="c-chat")
        record_ai_service_usage(self._user_a, "ai-assistant", correlation_id="c-mail")
        rows = db_optimizer.execute_query(
            """
            SELECT service_id, COUNT(*) AS c
            FROM service_usage_events
            WHERE user_id = ? AND event_type = 'ai_call'
            GROUP BY service_id
            """,
            (self._user_a,),
        )
        by_service = {r["service_id"]: int(r["c"]) for r in rows}
        self.assertEqual(by_service.get("chatbot"), 1)
        self.assertEqual(by_service.get("ai-assistant"), 1)

    def test_rollups_consistent_after_rebuild(self):
        record_automation_service_usage(
            self._user_a,
            rule_id=42,
            status="success",
            correlation_id="run-1",
        )
        record_automation_service_usage(
            self._user_a,
            rule_id=43,
            status="error",
            correlation_id="run-2",
        )
        updated = rebuild_daily_rollups_for_user(self._user_a, days=1)
        self.assertGreaterEqual(updated, 1)
        rollups = db_optimizer.execute_query(
            """
            SELECT SUM(event_count) AS events, SUM(failure_count) AS failures
            FROM service_daily_rollups
            WHERE user_id = ? AND metric_name = 'automation_executions'
            """,
            (self._user_a,),
        )
        self.assertGreaterEqual(int(rollups[0]["events"] or 0), 2)
        self.assertGreaterEqual(int(rollups[0]["failures"] or 0), 1)

    def test_billing_mirror_idempotent(self):
        if not db_optimizer.table_exists("billing_usage"):
            self.skipTest("billing_usage not available")
        month = "2099-01"
        db_optimizer.execute_query(
            "DELETE FROM billing_usage WHERE user_id = ? AND month = ?",
            (self._user_a, month),
            fetch=False,
        )
        db_optimizer.execute_query(
            "INSERT INTO billing_usage (user_id, month, usage_type, quantity) VALUES (?, ?, ?, ?)",
            (self._user_a, month, "chatbot_queries", 5),
            fetch=False,
        )
        first = mirror_billing_usage_to_analytics(self._user_a, month=month)
        second = mirror_billing_usage_to_analytics(self._user_a, month=month)
        self.assertGreaterEqual(first, 1)
        self.assertEqual(second, 0)
        mirror_rows = db_optimizer.execute_query(
            """
            SELECT COUNT(*) AS c FROM service_usage_events
            WHERE user_id = ? AND event_category = 'billing_mirror'
            """,
            (self._user_a,),
        )
        self.assertEqual(int(mirror_rows[0]["c"]), 1)

    def test_automation_health_metrics(self):
        health = get_automation_health(self._user_a, days=30)
        self.assertIn("success_rate", health)
        self.assertIn("total", health)

    @patch("analytics.service_usage_api.get_current_user_id", return_value=1)
    def test_summary_api_shape(self, _mock_uid):
        from flask import Flask
        from analytics.service_usage_api import service_usage_bp

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(service_usage_bp)
        with app.test_client() as client:
            response = client.get("/api/analytics/services/summary")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        payload = data.get("data", {})
        self.assertIn("user_id", payload)
        self.assertIn("billing_usage_month", payload)

    def test_refresh_tenant_analytics(self):
        record_service_usage_event(
            user_id=self._user_a,
            service_id="crm",
            event_type="service_enabled",
            metric_name="adoption",
            event_category="adoption",
        )
        counts = refresh_tenant_analytics(self._user_a, mirror_billing=False)
        self.assertIn("daily_rollups", counts)
        summary = get_tenant_service_summary(self._user_a)
        self.assertEqual(summary["user_id"], self._user_a)


if __name__ == "__main__":
    unittest.main()
