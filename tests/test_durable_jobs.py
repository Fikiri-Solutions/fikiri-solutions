#!/usr/bin/env python3
"""Durable background job framework tests."""

from __future__ import annotations

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

os.environ["FIKIRI_DURABLE_JOBS_PERSIST_IN_TEST"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.durable_jobs import (
    JOB_KIND_GMAIL_SYNC,
    JOB_KIND_KB_VECTORIZE,
    STATUS_COMPLETED,
    STATUS_DEAD,
    STATUS_PENDING,
    STATUS_RETRYING,
    build_idempotency_key,
    enqueue_durable_job,
    ensure_background_jobs_table,
    find_active_job_by_idempotency,
    get_durable_job,
    mark_job_completed,
    mark_job_failed,
    mark_job_running,
    run_durable_job,
)
from core.database_optimization import db_optimizer


class DurableJobsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_background_jobs_table()
        db_optimizer._initialize_database()

    def setUp(self):
        ensure_background_jobs_table()
        self.user_id = 88001
        self._ensure_user(self.user_id)
        db_optimizer.execute_query(
            "DELETE FROM background_jobs WHERE user_id = ?",
            (self.user_id,),
            fetch=False,
        )

    def _ensure_user(self, user_id: int) -> None:
        rows = db_optimizer.execute_query("SELECT id FROM users WHERE id = ?", (user_id,))
        if not rows:
            db_optimizer.execute_query(
                "INSERT INTO users (id, email, name, password_hash) VALUES (?, ?, ?, ?)",
                (user_id, f"durable-{user_id}@example.test", "Durable", "hash"),
                fetch=False,
            )

    def test_duplicate_job_prevention(self):
        key = build_idempotency_key("test", self.user_id, "dup")
        first = enqueue_durable_job(
            JOB_KIND_GMAIL_SYNC,
            user_id=self.user_id,
            idempotency_key=key,
            external_ref="gmail_sync_1",
        )
        second = enqueue_durable_job(
            JOB_KIND_GMAIL_SYNC,
            user_id=self.user_id,
            idempotency_key=key,
            external_ref="gmail_sync_2",
        )
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        active = find_active_job_by_idempotency(key, job_kind=JOB_KIND_GMAIL_SYNC)
        self.assertIsNotNone(active)
        self.assertEqual(active["external_ref"], "gmail_sync_1")

    def test_retry_safety_marks_dead_after_max(self):
        jid = enqueue_durable_job(
            JOB_KIND_KB_VECTORIZE,
            user_id=self.user_id,
            max_retries=2,
            payload={"doc_id": "doc-1"},
        )
        self.assertIsNotNone(jid)
        mark_job_running(jid)

        def failing_worker(_job):
            return {"success": False, "error": "transient"}

        r1 = run_durable_job(jid, failing_worker)
        self.assertTrue(r1.get("will_retry"))
        job = get_durable_job(jid)
        self.assertEqual(job["status"], STATUS_RETRYING)
        self.assertEqual(int(job["retry_count"]), 1)
        self.assertTrue(job.get("last_error"))

        mark_job_running(jid)
        r2 = run_durable_job(jid, failing_worker)
        self.assertFalse(r2.get("will_retry", True))
        job2 = get_durable_job(jid)
        self.assertIn(job2["status"], (STATUS_DEAD, "failed"))
        self.assertGreaterEqual(int(job2["retry_count"]), 2)
        self.assertEqual(int(job2.get("dead_letter") or 0), 1)

    def test_partial_failure_recovery_completes_on_retry(self):
        jid = enqueue_durable_job(JOB_KIND_KB_VECTORIZE, user_id=self.user_id, max_retries=3)
        attempts = {"n": 0}

        def flaky_worker(_job):
            attempts["n"] += 1
            if attempts["n"] < 2:
                return {"success": False, "error": "first fail"}
            return {"success": True, "vector_ids_count": 3}

        run_durable_job(jid, flaky_worker)
        mark_job_running(jid)
        result = run_durable_job(jid, flaky_worker)
        self.assertTrue(result.get("success"))
        job = get_durable_job(jid)
        self.assertEqual(job["status"], STATUS_COMPLETED)

    def test_structured_logging_fields_on_enqueue(self):
        with self.assertLogs("core.durable_jobs", level="INFO") as captured:
            jid = enqueue_durable_job(
                JOB_KIND_GMAIL_SYNC,
                user_id=self.user_id,
                correlation_id="corr-test-123",
                external_ref="ext-1",
            )
        self.assertIsNotNone(jid)
        self.assertTrue(any("job.enqueued" in r.message for r in captured.records))
        job = get_durable_job(jid)
        self.assertEqual(job.get("correlation_id"), "corr-test-123")
        self.assertEqual(job.get("job_kind"), JOB_KIND_GMAIL_SYNC)
        self.assertEqual(job.get("status"), STATUS_PENDING)

    def test_idempotent_kb_vectorize_fingerprint(self):
        from core.chatbot_vector_chunk_ingestion import _content_fingerprint

        h1 = _content_fingerprint("hello world")
        h2 = _content_fingerprint("hello world")
        h3 = _content_fingerprint("other")
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)

    def test_analytics_failure_does_not_break_primary_path(self):
        from analytics.service_activity_rollups import refresh_tenant_analytics

        with patch("analytics.service_activity_rollups._refresh_tenant_analytics_impl") as mock_impl:
            mock_impl.return_value = {"billing_mirrored": 0, "daily_rollups": 1, "tenant_metrics": 1}
            with patch("core.durable_jobs.enqueue_durable_job", side_effect=RuntimeError("db down")):
                counts = refresh_tenant_analytics(self.user_id, mirror_billing=False)
        self.assertEqual(counts["daily_rollups"], 1)

    def test_mark_completed_persists_result_json(self):
        jid = enqueue_durable_job(JOB_KIND_KB_VECTORIZE, user_id=self.user_id)
        mark_job_running(jid)
        mark_job_completed(jid, {"vector_ids_count": 5})
        rows = db_optimizer.execute_query(
            "SELECT status, result_json FROM background_jobs WHERE job_id = ?",
            (jid,),
        )
        self.assertEqual(rows[0]["status"], STATUS_COMPLETED)
        self.assertIn("vector_ids_count", rows[0]["result_json"] or "")


if __name__ == "__main__":
    unittest.main()
