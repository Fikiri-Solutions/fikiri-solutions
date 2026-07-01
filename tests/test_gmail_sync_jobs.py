#!/usr/bin/env python3
"""Gmail sync job manager tests."""

import unittest
import json
from contextlib import contextmanager
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database_optimization import DatabaseOptimizer
from email_automation.gmail_sync_jobs import (
    GmailSyncJobManager,
    abort_queued_gmail_sync_job,
    should_process_gmail_sync_inline,
)


class TestGmailSyncedEmailUpsert(unittest.TestCase):
    def test_upsert_synced_email_from_gmail_returns_row_id(self):
        optimizer = DatabaseOptimizer.__new__(DatabaseOptimizer)
        optimizer.ensure_synced_emails_upsert_constraint = MagicMock()
        optimizer.bind_boolean_column = MagicMock(return_value=1)
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = {"id": 321}

        @contextmanager
        def fake_transaction():
            yield conn, cursor

        optimizer.transaction = fake_transaction

        row_id = optimizer.upsert_synced_email_from_gmail(
            7,
            "gmail-1",
            "thread-1",
            "Subject",
            "from@example.com",
            "to@example.com",
            "2026-06-03T00:00:00",
            "Body",
            '["INBOX"]',
            1,
        )

        self.assertEqual(row_id, 321)
        cursor.execute.assert_called_once()
        self.assertIn("RETURNING id", cursor.execute.call_args.args[0])
        conn.commit.assert_called_once()


class TestGmailSyncInlinePolicy(unittest.TestCase):
    def test_inline_true_by_default(self):
        with patch.dict(
            os.environ,
            {"DATABASE_URL": "postgresql://user:pass@host:5432/db", "FIKIRI_GMAIL_SYNC_WORKER_ONLY": ""},
            clear=False,
        ):
            self.assertTrue(should_process_gmail_sync_inline())

    def test_inline_true_when_database_url_unset(self):
        with patch.dict(os.environ, {"DATABASE_URL": ""}, clear=False):
            self.assertTrue(should_process_gmail_sync_inline())

    def test_inline_false_when_worker_only(self):
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql://user:pass@host:5432/db",
                "FIKIRI_GMAIL_SYNC_WORKER_ONLY": "1",
            },
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


class TestGmailFullMessageFetch(unittest.TestCase):
    class _UsersResource:
        def __init__(self, messages_resource):
            self._messages_resource = messages_resource

        def messages(self):
            return self._messages_resource

    class _ServiceWithoutBatch:
        def __init__(self, messages_resource):
            self._users_resource = TestGmailFullMessageFetch._UsersResource(
                messages_resource
            )

        def users(self):
            return self._users_resource

    class _FakeBatch:
        def __init__(self, responses=None, exceptions=None, execute_error=None):
            self.responses = responses or {}
            self.exceptions = exceptions or {}
            self.execute_error = execute_error
            self.added_request_ids = []
            self._callbacks = []

        def add(self, request, callback, request_id=None):
            self.added_request_ids.append(request_id)
            self._callbacks.append((request_id, callback))

        def execute(self):
            if self.execute_error is not None:
                raise self.execute_error
            for request_id, callback in self._callbacks:
                callback(
                    request_id,
                    self.responses.get(request_id),
                    self.exceptions.get(request_id),
                )

    def _gmail_request(self, result=None, exc=None):
        request = MagicMock()
        if exc is not None:
            request.execute.side_effect = exc
        else:
            request.execute.return_value = result
        return request

    def test_fetch_full_gmail_messages_returns_requested_order(self):
        manager = GmailSyncJobManager.__new__(GmailSyncJobManager)
        service = MagicMock()
        messages_resource = service.users.return_value.messages.return_value
        messages_resource.get.side_effect = [
            self._gmail_request({"id": "m1"}),
            self._gmail_request({"id": "m2"}),
            self._gmail_request({"id": "m3"}),
        ]

        result = manager._fetch_full_gmail_messages(service, ["m1", "m2", "m3"])

        self.assertEqual([message["id"] for message in result], ["m1", "m2", "m3"])
        self.assertEqual(
            [call.kwargs["id"] for call in messages_resource.get.call_args_list],
            ["m1", "m2", "m3"],
        )
        for call in messages_resource.get.call_args_list:
            self.assertEqual(call.kwargs["userId"], "me")
            self.assertEqual(call.kwargs["format"], "full")

    def test_fetch_full_gmail_messages_skips_failed_fetch_and_continues(self):
        manager = GmailSyncJobManager.__new__(GmailSyncJobManager)
        service = MagicMock()
        messages_resource = service.users.return_value.messages.return_value
        messages_resource.get.side_effect = [
            self._gmail_request({"id": "m1"}),
            self._gmail_request(exc=RuntimeError("temporary Gmail failure")),
            self._gmail_request({"id": "m3"}),
        ]

        result = manager._fetch_full_gmail_messages(service, ["m1", "m2", "m3"])

        self.assertEqual([message["id"] for message in result], ["m1", "m3"])
        self.assertEqual(messages_resource.get.call_count, 3)

    def test_fetch_full_gmail_messages_batch_unavailable_falls_back_to_serial(self):
        manager = GmailSyncJobManager.__new__(GmailSyncJobManager)
        messages_resource = MagicMock()
        service = self._ServiceWithoutBatch(messages_resource)

        with patch.object(
            manager,
            "_fetch_full_gmail_messages_serial",
            return_value=[{"id": "m1"}],
        ) as mock_serial:
            result = manager._fetch_full_gmail_messages(service, ["m1"], mode="batch")

        self.assertEqual(result, [{"id": "m1"}])
        mock_serial.assert_called_once_with(service, ["m1"])

    def test_fetch_full_gmail_messages_batch_success_returns_ordered_messages(self):
        manager = GmailSyncJobManager.__new__(GmailSyncJobManager)
        service = MagicMock()
        messages_resource = service.users.return_value.messages.return_value
        messages_resource.get.side_effect = lambda **kwargs: {"request_id": kwargs["id"]}
        batch = self._FakeBatch(
            responses={
                "m2": {"id": "m2"},
                "m1": {"id": "m1"},
                "m3": {"id": "m3"},
            }
        )
        service.new_batch_http_request.return_value = batch

        result = manager._fetch_full_gmail_messages(
            service, ["m1", "m2", "m3"], mode="batch"
        )

        self.assertEqual([message["id"] for message in result], ["m1", "m2", "m3"])
        self.assertEqual(batch.added_request_ids, ["m1", "m2", "m3"])
        for call in messages_resource.get.call_args_list:
            self.assertEqual(call.kwargs["userId"], "me")
            self.assertEqual(call.kwargs["format"], "full")

    def test_fetch_full_gmail_messages_batch_partial_failure_skips_failed_id(self):
        manager = GmailSyncJobManager.__new__(GmailSyncJobManager)
        service = MagicMock()
        service.users.return_value.messages.return_value.get.side_effect = (
            lambda **kwargs: {"request_id": kwargs["id"]}
        )
        service.new_batch_http_request.return_value = self._FakeBatch(
            responses={"m1": {"id": "m1"}, "m3": {"id": "m3"}},
            exceptions={"m2": RuntimeError("message failed")},
        )

        result = manager._fetch_full_gmail_messages(
            service, ["m1", "m2", "m3"], mode="batch"
        )

        self.assertEqual([message["id"] for message in result], ["m1", "m3"])

    def test_fetch_full_gmail_messages_global_batch_failure_falls_back_to_serial(self):
        manager = GmailSyncJobManager.__new__(GmailSyncJobManager)
        service = MagicMock()
        service.users.return_value.messages.return_value.get.side_effect = (
            lambda **kwargs: {"request_id": kwargs["id"]}
        )
        service.new_batch_http_request.return_value = self._FakeBatch(
            responses={"m1": {"id": "m1"}},
            execute_error=RuntimeError("batch transport failed"),
        )

        with patch.object(
            manager,
            "_fetch_full_gmail_messages_serial",
            return_value=[{"id": "m1"}, {"id": "m2"}],
        ) as mock_serial:
            result = manager._fetch_full_gmail_messages(
                service, ["m1", "m2"], mode="batch"
            )

        self.assertEqual([message["id"] for message in result], ["m1", "m2"])
        mock_serial.assert_called_once_with(service, ["m1", "m2"])

    def test_fetch_full_gmail_messages_serial_mode_does_not_use_batch(self):
        manager = GmailSyncJobManager.__new__(GmailSyncJobManager)
        service = MagicMock()

        with patch.object(
            manager,
            "_fetch_full_gmail_messages_serial",
            return_value=[{"id": "m1"}],
        ) as mock_serial, patch.object(
            manager, "_fetch_full_gmail_messages_batch"
        ) as mock_batch:
            result = manager._fetch_full_gmail_messages(service, ["m1"], mode="serial")

        self.assertEqual(result, [{"id": "m1"}])
        mock_serial.assert_called_once_with(service, ["m1"])
        mock_batch.assert_not_called()

    def test_get_gmail_messages_returns_shape_and_uses_full_fetch_helper(self):
        manager = GmailSyncJobManager.__new__(GmailSyncJobManager)
        manager.sync_page_size = 50
        service = MagicMock()
        messages_resource = service.users.return_value.messages.return_value
        messages_resource.list.return_value = self._gmail_request(
            {
                "messages": [{"id": "m1"}, {"id": "m2"}],
                "nextPageToken": "page-2",
            }
        )
        full_messages = [
            {"id": "m1", "payload": {"headers": []}},
            {"id": "m2", "payload": {"headers": []}},
        ]

        with patch.object(
            manager, "_fetch_full_gmail_messages", return_value=full_messages
        ) as mock_fetch:
            result = manager._get_gmail_messages(
                service,
                lookback_days=7,
                max_messages=2,
            )

        self.assertEqual(result["messages"], full_messages)
        self.assertEqual(result["next_page_token"], "page-2")
        self.assertTrue(result["has_more"])
        mock_fetch.assert_called_once_with(service, ["m1", "m2"])
        messages_resource.list.assert_called_once()


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


    @patch.dict(os.environ, {"MAILBOX_AUTOMATION_ENABLED": "false"}, clear=False)
    @patch("email_automation.gmail_sync_jobs.db_optimizer")
    def test_sync_logs_email_received_event_with_store_email_id_without_post_upsert_select(
        self, mock_db
    ):
        manager = GmailSyncJobManager.__new__(GmailSyncJobManager)
        manager.sync_days = 7
        manager.sync_max_messages = 1
        manager.progress_update_every = 10
        message = {"id": "gmail-123", "threadId": "thread-123", "payload": {"headers": []}}
        mock_db.execute_query.return_value = []

        with patch.object(
            manager,
            "_get_gmail_messages",
            return_value={"messages": [message], "has_more": False},
        ), patch.object(manager, "_store_email", return_value=123), patch.object(
            manager, "_extract_contacts", return_value=[]
        ), patch.object(manager, "_calculate_lead_score", return_value=0), patch(
            "email_automation.email_event_log.record_email_event"
        ) as mock_record_event, patch(
            "email_automation.email_workflow_state.should_classify_email",
            return_value=False,
        ), patch(
            "email_automation.pipeline.orchestrate_incoming",
            return_value={"success": True},
        ):
            result = manager._sync_emails(
                MagicMock(), user_id=3, job_id="job-event-id", job_meta={}
            )

        self.assertEqual(result.get("emails_synced"), 1)
        mock_record_event.assert_called_once()
        self.assertEqual(mock_record_event.call_args.kwargs.get("synced_email_id"), 123)
        post_upsert_selects = [
            call
            for call in mock_db.execute_query.call_args_list
            if "SELECT id FROM synced_emails" in str(call.args[0])
        ]
        self.assertEqual(post_upsert_selects, [])

    @patch("email_automation.gmail_sync_jobs.db_optimizer")
    def test_store_email_returns_synced_email_row_id(self, mock_db):
        manager = GmailSyncJobManager.__new__(GmailSyncJobManager)
        mock_db.upsert_synced_email_from_gmail.return_value = 987
        message = {
            "id": "gmail-store-1",
            "threadId": "thread-store-1",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Hello"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "owner@example.com"},
                    {"name": "Date", "value": "Wed, 03 Jun 2026 12:00:00 +0000"},
                ],
                "body": {"data": "SGVsbG8="},
            },
        }

        row_id = manager._store_email(3, message)

        self.assertEqual(row_id, 987)
        mock_db.upsert_synced_email_from_gmail.assert_called_once()


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
