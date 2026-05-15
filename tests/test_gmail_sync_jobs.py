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
