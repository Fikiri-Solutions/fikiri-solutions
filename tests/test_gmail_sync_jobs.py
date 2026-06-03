#!/usr/bin/env python3
"""Gmail sync job manager tests."""

import unittest
import json
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from email_automation.gmail_sync_jobs import (
    GmailSyncJobManager,
    abort_queued_gmail_sync_job,
    should_process_gmail_sync_inline,
)


class TestGmailSyncInlinePolicy(unittest.TestCase):
    def test_inline_true_for_sqlite_url(self):
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///data/fikiri.db"}, clear=False):
            self.assertTrue(should_process_gmail_sync_inline())

    def test_inline_true_when_database_url_unset(self):
        with patch.dict(os.environ, {"DATABASE_URL": ""}, clear=False):
            self.assertTrue(should_process_gmail_sync_inline())

    def test_inline_false_for_postgres(self):
        with patch.dict(
            os.environ,
            {"DATABASE_URL": "postgresql://user:pass@host:5432/db"},
            clear=False,
        ):
            self.assertFalse(should_process_gmail_sync_inline())

    @patch("email_automation.gmail_sync_jobs.db_optimizer")
    def test_abort_queued_gmail_sync_job_marks_failed(self, mock_db):
        abort_queued_gmail_sync_job("job-1", 42, "queue down")
        self.assertEqual(mock_db.execute_query.call_count, 1)
        mock_db.upsert_user_sync_status_merge.assert_called_once_with(
            42,
            sync_status="failed",
            syncing=0,
        )


class TestGmailSyncJobs(unittest.TestCase):
    @patch('email_automation.gmail_sync_jobs.should_process_gmail_sync_inline', return_value=False)
    @patch('email_automation.gmail_sync_jobs.db_optimizer')
    @patch('email_automation.gmail_sync_jobs.time.time')
    def test_queue_sync_job_writes_db_and_redis(self, mock_time, mock_db, _inline):
        manager = GmailSyncJobManager()
        manager.redis_client = MagicMock()
        mock_time.return_value = 1234567890
        with patch(
            "core.durable_jobs.find_active_job_by_idempotency",
            return_value=None,
        ), patch(
            "core.durable_jobs.enqueue_durable_job",
            return_value="durable-test-1",
        ):
            job_id = manager.queue_sync_job(user_id=1, sync_type='full', metadata={'source': 'test'})

        self.assertEqual(job_id, 'gmail_sync_1_1234567890')
        self.assertTrue(mock_db.execute_query.called)
        manager.redis_client.lpush.assert_called_once()

    @patch('email_automation.gmail_sync_jobs.db_optimizer')
    def test_process_sync_job_not_found(self, mock_db):
        manager = GmailSyncJobManager()
        mock_db.execute_query.return_value = []

        result = manager.process_sync_job('missing')

        self.assertFalse(result.get('success'))
        self.assertEqual(result.get('error_code'), 'JOB_NOT_FOUND')

    @patch('email_automation.gmail_sync_jobs.gmail_client')
    @patch('email_automation.gmail_sync_jobs.db_optimizer')
    def test_process_sync_job_gmail_unavailable_marks_failed(self, mock_db, mock_gmail_client):
        manager = GmailSyncJobManager()
        mock_db.execute_query.side_effect = [
            [{'user_id': 1, 'job_id': 'job'}],
            None,
            None,
            None
        ]

        with patch('email_automation.gmail_sync_jobs.GMAIL_API_AVAILABLE', False):
            result = manager.process_sync_job('job')

        self.assertFalse(result.get('success'))
        self.assertEqual(result.get('error_code'), 'SYNC_PROCESSING_FAILED')
        self.assertTrue(mock_db.execute_query.called)


class TestGmailSyncCostControls(unittest.TestCase):
    @patch.dict(os.environ, {"MAILBOX_AUTOMATION_ENABLED": "false"}, clear=False)
    @patch("email_automation.gmail_sync_jobs.db_optimizer")
    def test_sync_throttles_progress_writes_and_reuses_owner_email(self, mock_db):
        manager = GmailSyncJobManager.__new__(GmailSyncJobManager)
        manager.sync_days = 7
        manager.sync_max_messages = 25
        manager.progress_update_every = 10

        messages = [
            {"id": f"m{i}", "threadId": f"t{i}", "payload": {"headers": []}}
            for i in range(25)
        ]
        mock_db.execute_query.return_value = []

        with patch.object(
            manager,
            "_get_gmail_messages",
            return_value={"messages": messages, "has_more": False},
        ), patch.object(manager, "_store_email", return_value=1), patch.object(
            manager, "_extract_contacts", return_value=[]
        ), patch.object(manager, "_calculate_lead_score", return_value=0), patch(
            "email_automation.email_workflow_state.should_classify_email",
            return_value=False,
        ), patch(
            "email_automation.pipeline.orchestrate_incoming",
            return_value={"success": True},
        ):
            result = manager._sync_emails(
                MagicMock(), user_id=3, job_id="job-cost-1", job_meta={}
            )

        self.assertEqual(result.get("emails_synced"), 25)

        progress_updates = [
            call
            for call in mock_db.execute_query.call_args_list
            if "SET progress = ?, emails_synced = ?" in str(call.args[0])
        ]
        self.assertEqual(len(progress_updates), 4)
        self.assertEqual(
            [call.args[1][1] for call in progress_updates],
            [1, 10, 20, 25],
        )
        self.assertEqual(mock_db.upsert_user_sync_status_merge.call_count, 4)

        owner_queries = [
            call
            for call in mock_db.execute_query.call_args_list
            if "SELECT email FROM users WHERE id = ? LIMIT 1" in str(call.args[0])
        ]
        self.assertEqual(len(owner_queries), 1)



class TestEmailBodyExtraction(unittest.TestCase):
    def test_extract_email_body_prefers_html(self):
        manager = GmailSyncJobManager.__new__(GmailSyncJobManager)
        payload = {
            'parts': [
                {'mimeType': 'text/plain', 'body': {'data': 'dGV4dA=='}},
                {'mimeType': 'text/html', 'body': {'data': 'PGgxPkhlbGxvPC9oMT4='}}
            ]
        }
        body = manager._extract_email_body(payload)
        self.assertIn('<h1>Hello</h1>', body)

    def test_extract_email_body_fallback_text(self):
        manager = GmailSyncJobManager.__new__(GmailSyncJobManager)
        payload = {
            'parts': [
                {'mimeType': 'text/plain', 'body': {'data': 'dGV4dA=='}}
            ]
        }
        body = manager._extract_email_body(payload)
        self.assertEqual(body, 'text')


if __name__ == '__main__':
    unittest.main()
