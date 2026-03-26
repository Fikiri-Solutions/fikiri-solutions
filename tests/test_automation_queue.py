#!/usr/bin/env python3
"""Tests for services/automation_queue.py – job creation, processing, status."""

import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


class TestAutomationQueue(unittest.TestCase):
    @patch("services.automation_queue.db_optimizer")
    def test_queue_automation_job_creates_job(self, mock_db):
        mock_db.execute_query.return_value = None
        from services.automation_queue import AutomationJobManager

        mgr = AutomationJobManager()
        job_id = mgr.queue_automation_job(1, rule_ids=[1, 2])
        self.assertIsNotNone(job_id)
        self.assertTrue(job_id.startswith("automation_"))
        mock_db.execute_query.assert_called()

    @patch("services.automation_queue.db_optimizer")
    def test_queue_automation_job_stores_correlation_on_rule_ids(self, mock_db):
        mock_db.execute_query.return_value = None
        from services.automation_queue import AutomationJobManager

        mgr = AutomationJobManager()
        mgr.queue_automation_job(1, rule_ids=[9], correlation_id="trace-abc")
        insert_calls = [
            c for c in mock_db.execute_query.call_args_list
            if c.args and "INSERT INTO automation_jobs" in (c.args[0] or "")
        ]
        self.assertTrue(insert_calls)
        payload = json.loads(insert_calls[0].args[1][3])
        self.assertEqual(payload.get("correlation_id"), "trace-abc")
        self.assertEqual(payload.get("rule_ids"), [9])

    @patch("services.automation_queue.db_optimizer")
    def test_queue_automation_job_merges_correlation_into_trigger_data(self, mock_db):
        mock_db.execute_query.return_value = None
        from services.automation_queue import AutomationJobManager

        mgr = AutomationJobManager()
        mgr.queue_automation_job(
            1,
            trigger_type="lead_created",
            trigger_data={"lead_id": 5},
            correlation_id="t-1",
        )
        insert_calls = [
            c for c in mock_db.execute_query.call_args_list
            if c.args and "INSERT INTO automation_jobs" in (c.args[0] or "")
        ]
        payload = json.loads(insert_calls[0].args[1][3])
        self.assertEqual(payload.get("correlation_id"), "t-1")
        self.assertEqual(payload.get("trigger_data", {}).get("correlation_id"), "t-1")

    @patch("services.automation_queue.db_optimizer")
    def test_queue_automation_job_returns_none_when_missing_args(self, mock_db):
        from services.automation_queue import AutomationJobManager

        mgr = AutomationJobManager()
        self.assertIsNone(mgr.queue_automation_job(1))

    @patch("services.automation_queue._get_engine")
    @patch("services.automation_queue.db_optimizer")
    def test_process_automation_job_rule_ids_success(self, mock_db, mock_get_engine):
        def query_side_effect(*args, **kwargs):
            q = args[0] if args else ""
            if "WHERE job_id = ?" in q and "SELECT" in q:
                return [{"job_id": "j1", "user_id": 1, "payload_type": "rule_ids", "payload_json": json.dumps({"rule_ids": [1]}), "attempt": 0, "max_attempts": 3, "status": "queued"}]
            return None

        mock_db.execute_query.side_effect = query_side_effect
        mock_engine = MagicMock()
        mock_engine.execute_rules.return_value = [{"rule_id": 1, "success": True}]
        mock_get_engine.return_value = mock_engine

        from services.automation_queue import AutomationJobManager

        mgr = AutomationJobManager()
        result = mgr.process_automation_job("j1")
        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("status"), "success")
        self.assertIn("execution_results", result)

    @patch("services.automation_queue._get_engine")
    @patch("services.automation_queue.db_optimizer")
    def test_process_automation_job_rule_ids_one_failed(self, mock_db, mock_get_engine):
        """Job is marked failed when any rule returns success=False (not only NOT_IMPLEMENTED)."""
        def query_side_effect(*args, **kwargs):
            q = args[0] if args else ""
            if "WHERE job_id = ?" in q and "SELECT" in q:
                return [{"job_id": "j1", "user_id": 1, "payload_type": "rule_ids", "payload_json": json.dumps({"rule_ids": [1, 2]}), "attempt": 0, "max_attempts": 3, "status": "queued"}]
            return None

        mock_db.execute_query.side_effect = query_side_effect
        mock_engine = MagicMock()
        mock_engine.execute_rules.return_value = [
            {"rule_id": 1, "success": True},
            {"rule_id": 2, "success": False, "error": "Webhook delivery failed"},
        ]
        mock_get_engine.return_value = mock_engine

        from services.automation_queue import AutomationJobManager

        mgr = AutomationJobManager()
        result = mgr.process_automation_job("j1")
        self.assertFalse(result.get("success"))
        self.assertEqual(result.get("status"), "failed")
        self.assertIn("execution_results", result)

    @patch("services.automation_queue.db_optimizer")
    def test_queue_automation_job_idempotency_blocks_queued(self, mock_db):
        """Idempotency blocks duplicate when existing job is queued (not only success)."""
        from services.automation_queue import AutomationJobManager, AUTOMATION_JOB_QUEUED

        def side_effect(*args, **kwargs):
            q = args[0] if args else ""
            if "idempotency_key" in q and "status" in q and "ORDER BY" in q:
                return [{"job_id": "existing", "status": AUTOMATION_JOB_QUEUED}]
            return None

        mock_db.execute_query.side_effect = side_effect

        mgr = AutomationJobManager()
        job_id = mgr.queue_automation_job(1, rule_ids=[1], idempotency_key="same-key")
        self.assertIsNone(job_id)
        mock_db.execute_query.return_value = []

        from services.automation_queue import AutomationJobManager

        mgr = AutomationJobManager()
        result = mgr.process_automation_job("nonexistent")
        self.assertFalse(result.get("success"))
        self.assertEqual(result.get("error"), "Job not found")

    @patch("services.automation_queue.db_optimizer")
    def test_get_job_status_returns_none_for_missing(self, mock_db):
        mock_db.execute_query.return_value = []

        from services.automation_queue import AutomationJobManager

        mgr = AutomationJobManager()
        self.assertIsNone(mgr.get_job_status("nonexistent"))

    @patch("services.automation_queue.db_optimizer")
    def test_get_queue_depth_returns_dict(self, mock_db):
        mock_db.execute_query.return_value = [{"status": "success", "cnt": 5}, {"status": "queued", "cnt": 2}]

        from services.automation_queue import AutomationJobManager

        mgr = AutomationJobManager()
        depth = mgr.get_queue_depth()
        self.assertIn("queued", depth)
        self.assertIn("success", depth)
        self.assertIn("dead", depth)
        self.assertEqual(depth["success"], 5)
        self.assertEqual(depth["queued"], 2)

    @patch("services.automation_queue.db_optimizer")
    def test_get_automation_metrics_returns_rates_and_p95(self, mock_db):
        def query_side_effect(*args, **kwargs):
            q = args[0] if args else ""
            if "GROUP BY status" in q:
                return [{"status": "success", "cnt": 10}, {"status": "failed", "cnt": 1}]
            if "started_at" in q and "completed_at" in q:
                return [
                    {"started_at": "2025-01-01T12:00:00", "completed_at": "2025-01-01T12:00:02"},
                    {"started_at": "2025-01-01T12:01:00", "completed_at": "2025-01-01T12:01:05"},
                ]
            return []

        mock_db.execute_query.side_effect = query_side_effect

        from services.automation_queue import AutomationJobManager

        mgr = AutomationJobManager()
        metrics = mgr.get_automation_metrics(user_id=1, hours=24)
        self.assertIn("success_rate_24h", metrics)
        self.assertEqual(metrics["success_rate_24h"], 10 / 11)
        self.assertIn("p95_duration_seconds", metrics)
        self.assertIsNotNone(metrics["p95_duration_seconds"])
