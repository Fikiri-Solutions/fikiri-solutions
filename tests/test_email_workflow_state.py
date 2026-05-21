#!/usr/bin/env python3
"""Email workflow state Phase A+B."""

import json
import os
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database_optimization import db_optimizer
from core.email_triage_store import (
    count_classifications_by_category,
    ensure_email_classifications_table,
    list_classified_emails,
    upsert_classification,
)
from email_automation.email_workflow_state import (
    ensure_email_workflow_state_table,
    get_or_create_workflow_state,
    mark_action_applied,
    mark_classified,
    mark_reclassified,
    should_classify_email,
    workflow_status_is_handled,
)
from services.email_triage_service import (
    classify_unclassified_synced,
    execute_bulk_action,
    reclassify_synced_messages,
)

# Distinct user ids per class avoid cross-test cleanup races on shared SQLite CI DB.
_USER_WORKFLOW_BASE = 91_001
_WORKFLOW_DB_LOCK = threading.RLock()


@pytest.fixture(autouse=True)
def _serialize_workflow_state_db():
    """Serializes this module's DB writes on the shared CI SQLite file."""
    with _WORKFLOW_DB_LOCK:
        yield


def _ensure_workflow_test_user(user_id: int) -> None:
    """synced_emails.user_id FK requires a users row."""
    db_optimizer.execute_query(
        """
        INSERT OR IGNORE INTO users (id, email, name, password_hash)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, f"wf-test-{user_id}@example.test", "Workflow Test", "hash"),
        fetch=False,
    )
    row = db_optimizer.execute_query("SELECT id FROM users WHERE id = ?", (user_id,))
    if not row:
        raise AssertionError(f"workflow test user {user_id} missing after ensure")


def _execute_with_sqlite_retry(query: str, params: tuple, *, fetch: bool = False) -> None:
    for attempt in range(4):
        try:
            db_optimizer.execute_query(query, params, fetch=fetch)
            return
        except Exception as exc:
            if "locked" not in str(exc).lower() or attempt >= 3:
                raise
            time.sleep(0.05 * (attempt + 1))


def _cleanup_workflow_test_user(user_id: int) -> None:
    """Best-effort teardown; order respects child tables first."""
    for tbl in ("email_workflow_state", "email_classifications", "synced_emails"):
        try:
            _execute_with_sqlite_retry(
                f"DELETE FROM {tbl} WHERE user_id = ?",
                (user_id,),
            )
        except Exception:
            pass
    try:
        _execute_with_sqlite_retry(
            "DELETE FROM users WHERE id = ?",
            (user_id,),
        )
    except Exception:
        pass


def _insert_synced_email_row(
    user_id: int,
    external_id: str,
    *,
    subject: str = "Hello",
    sender: str = "a@b.com",
    body: str = "body",
    date: str = "2026-05-20",
    labels: str | None = None,
) -> None:
    _ensure_workflow_test_user(user_id)
    if labels is None:
        db_optimizer.execute_query(
            """
            INSERT INTO synced_emails (
                user_id, gmail_id, external_id, provider, subject, sender, body, date
            ) VALUES (?, ?, ?, 'gmail', ?, ?, ?, ?)
            """,
            (user_id, external_id, external_id, subject, sender, body, date),
            fetch=False,
        )
    else:
        db_optimizer.execute_query(
            """
            INSERT INTO synced_emails (
                user_id, gmail_id, external_id, provider, subject, sender, body, date, labels
            ) VALUES (?, ?, ?, 'gmail', ?, ?, ?, ?, ?)
            """,
            (user_id, external_id, external_id, subject, sender, body, date, labels),
            fetch=False,
        )


class TestEmailWorkflowState(unittest.TestCase):
    def setUp(self):
        ensure_email_workflow_state_table()
        ensure_email_classifications_table()
        self.user_id = _USER_WORKFLOW_BASE
        self.ext_id = "wf-test-msg-001"
        _ensure_workflow_test_user(self.user_id)

    def tearDown(self):
        _cleanup_workflow_test_user(self.user_id)

    def test_mark_classified_idempotent(self):
        mark_classified(self.user_id, self.ext_id, provider="gmail", source="test")
        mark_classified(self.user_id, self.ext_id, provider="gmail", source="test")
        row = get_or_create_workflow_state(self.user_id, self.ext_id, provider="gmail")
        self.assertEqual(row["classification_status"], "classified")
        self.assertEqual(int(row["classification_version"] or 0), 0)

    def test_mark_classified_upsert_sql_qualifies_columns_for_postgres(self):
        """Postgres ON CONFLICT requires table-qualified refs (excluded vs existing row)."""
        import inspect
        from email_automation import email_workflow_state as wf_mod

        classified_src = inspect.getsource(wf_mod.mark_classified)
        reclassified_src = inspect.getsource(wf_mod.mark_reclassified)
        self.assertIn("email_workflow_state.classification_status", classified_src)
        self.assertIn("email_workflow_state.workflow_status", classified_src)
        self.assertNotIn("WHEN classification_status =", classified_src)
        self.assertIn("email_workflow_state.classification_version + 1", reclassified_src)

    def test_should_classify_false_after_classified(self):
        mark_classified(self.user_id, self.ext_id, provider="gmail")
        self.assertFalse(should_classify_email(self.user_id, self.ext_id, "gmail", force=False))

    def test_should_classify_true_with_force(self):
        mark_classified(self.user_id, self.ext_id, provider="gmail")
        self.assertTrue(should_classify_email(self.user_id, self.ext_id, "gmail", force=True))

    def test_backfill_from_existing_classification(self):
        upsert_classification(
            self.user_id,
            external_id=self.ext_id,
            provider="gmail",
            triage={
                "category": "review_needed",
                "lead_score": 20,
                "business_relevance_score": 30,
                "urgency_score": 25,
                "cleanup_action": "keep",
                "confidence": 0.5,
                "reason": "backfill test",
            },
        )
        self.assertFalse(should_classify_email(self.user_id, self.ext_id, "gmail", force=False))
        row = get_or_create_workflow_state(self.user_id, self.ext_id, provider="gmail")
        self.assertEqual(row["classification_status"], "classified")

    def test_reclassify_increments_version(self):
        mark_classified(self.user_id, self.ext_id, provider="gmail")
        mark_reclassified(self.user_id, self.ext_id, provider="gmail")
        row = get_or_create_workflow_state(self.user_id, self.ext_id, provider="gmail")
        self.assertEqual(row["classification_status"], "reclassified")
        self.assertGreaterEqual(int(row["classification_version"] or 0), 1)
        self.assertEqual(row["last_action"], "reclassify")
        self.assertEqual(row["last_action_source"], "command_center")

    def test_handled_excluded_from_active_list(self):
        upsert_classification(
            self.user_id,
            external_id=self.ext_id,
            provider="gmail",
            triage={
                "category": "business_lead",
                "lead_score": 70,
                "business_relevance_score": 70,
                "urgency_score": 50,
                "cleanup_action": "keep",
                "confidence": 0.8,
                "reason": "lead test",
            },
        )
        mark_classified(self.user_id, self.ext_id, provider="gmail")
        mark_action_applied(
            self.user_id,
            self.ext_id,
            action="archive",
            provider="gmail",
            source="test",
        )
        active = list_classified_emails(
            self.user_id, category="business_lead", include_handled=False
        )
        ids = [e["id"] for e in active.get("emails") or []]
        self.assertNotIn(self.ext_id, ids)
        all_rows = list_classified_emails(
            self.user_id, category="business_lead", include_handled=True
        )
        all_ids = [e["id"] for e in all_rows.get("emails") or []]
        self.assertIn(self.ext_id, all_ids)

    def test_category_counts_exclude_handled(self):
        ext2 = "wf-test-msg-002"
        upsert_classification(
            self.user_id,
            external_id=ext2,
            provider="gmail",
            triage={
                "category": "business_lead",
                "lead_score": 60,
                "business_relevance_score": 60,
                "urgency_score": 40,
                "cleanup_action": "keep",
                "confidence": 0.7,
                "reason": "active lead",
            },
        )
        mark_classified(self.user_id, ext2, provider="gmail")
        upsert_classification(
            self.user_id,
            external_id=self.ext_id,
            provider="gmail",
            triage={
                "category": "business_lead",
                "lead_score": 70,
                "business_relevance_score": 70,
                "urgency_score": 50,
                "cleanup_action": "keep",
                "confidence": 0.8,
                "reason": "archived lead",
            },
        )
        mark_classified(self.user_id, self.ext_id, provider="gmail")
        mark_action_applied(self.user_id, self.ext_id, action="archive", provider="gmail")
        active_leads = list_classified_emails(
            self.user_id, category="business_lead", include_handled=False
        )
        active_ids = {e["id"] for e in active_leads.get("emails") or []}
        self.assertIn(ext2, active_ids)
        self.assertNotIn(self.ext_id, active_ids)
        counts_all = count_classifications_by_category(self.user_id, include_handled=True)
        self.assertGreaterEqual(counts_all.get("business_lead", 0), 2)

    def test_workflow_status_is_handled(self):
        self.assertTrue(workflow_status_is_handled("archived"))
        self.assertFalse(workflow_status_is_handled("active"))


class TestClassifyUnclassifiedWorkflow(unittest.TestCase):
    def setUp(self):
        ensure_email_workflow_state_table()
        ensure_email_classifications_table()
        self.user_id = _USER_WORKFLOW_BASE + 1
        self.ext_id = "wf-unclassified-001"
        _ensure_workflow_test_user(self.user_id)

    def tearDown(self):
        _cleanup_workflow_test_user(self.user_id)

    def test_classify_unclassified_returns_counts(self):
        _insert_synced_email_row(self.user_id, self.ext_id)
        result = classify_unclassified_synced(self.user_id, limit=10)
        self.assertIn("count", result)
        self.assertIn("scanned", result)
        self.assertIn("skipped_existing", result)
        self.assertGreaterEqual(result["scanned"], 1)


class TestGmailSyncSkipsClassified(unittest.TestCase):
    def test_sync_guard_does_not_call_triage_when_classified(self):
        """Mirrors gmail_sync_jobs guard: should_classify_email False => no triage."""
        user_id = _USER_WORKFLOW_BASE + 2
        ext = "wf-sync-skip-001"
        ensure_email_workflow_state_table()
        _ensure_workflow_test_user(user_id)
        try:
            mark_classified(user_id, ext, provider="gmail")
            with patch(
                "services.email_triage_service.triage_and_store_synced_message"
            ) as mock_triage:
                if should_classify_email(user_id, ext, "gmail", force=False):
                    mock_triage(user_id, external_id=ext, subject="", body="")
                mock_triage.assert_not_called()
        finally:
            _cleanup_workflow_test_user(user_id)


class TestReclassifyService(unittest.TestCase):
    def setUp(self):
        ensure_email_workflow_state_table()
        ensure_email_classifications_table()
        self.user_id = _USER_WORKFLOW_BASE + 3
        self.ext_id = "wf-reclass-001"
        _ensure_workflow_test_user(self.user_id)

    def tearDown(self):
        _cleanup_workflow_test_user(self.user_id)

    def test_reclassify_overwrites_and_marks_reclassified(self):
        _insert_synced_email_row(
            self.user_id,
            self.ext_id,
            subject="API usage threshold",
            sender="noreply@openai.com",
            body="alert",
        )
        upsert_classification(
            self.user_id,
            external_id=self.ext_id,
            triage={
                "category": "business_lead",
                "lead_score": 60,
                "business_relevance_score": 60,
                "urgency_score": 50,
                "cleanup_action": "keep",
                "confidence": 0.65,
                "reason": "old",
            },
        )
        mark_classified(self.user_id, self.ext_id, provider="gmail")
        result = reclassify_synced_messages(self.user_id, [self.ext_id])
        self.assertGreaterEqual(result["count"], 1)
        row = get_or_create_workflow_state(self.user_id, self.ext_id, provider="gmail")
        self.assertEqual(row["classification_status"], "reclassified")
        listed = list_classified_emails(self.user_id, category="action_needed", limit=20)
        ids = [e["id"] for e in listed.get("emails") or []]
        self.assertIn(self.ext_id, ids)


class TestPhaseCWorkflowPersistence(unittest.TestCase):
    """Phase C: user actions persist to email_workflow_state."""

    def setUp(self):
        ensure_email_workflow_state_table()
        ensure_email_classifications_table()
        self.user_id = _USER_WORKFLOW_BASE + 4
        self.ext_id = "wf-phasec-001"
        _ensure_workflow_test_user(self.user_id)

    def tearDown(self):
        _cleanup_workflow_test_user(self.user_id)

    def _seed_lead(self, ext_id: str, lead_score: int = 70):
        upsert_classification(
            self.user_id,
            external_id=ext_id,
            provider="gmail",
            triage={
                "category": "business_lead",
                "lead_score": lead_score,
                "business_relevance_score": lead_score,
                "urgency_score": 50,
                "cleanup_action": "keep",
                "confidence": 0.8,
                "reason": "phase c",
            },
        )
        mark_classified(self.user_id, ext_id, provider="gmail")

    @patch("integrations.gmail.gmail_client.gmail_client.get_gmail_service_for_user")
    def test_bulk_archive_sets_archived_and_hides(self, mock_gmail):
        self._seed_lead(self.ext_id)
        gmail_service = MagicMock()
        gmail_service.users().messages().modify().execute.return_value = {}
        mock_gmail.return_value = gmail_service

        result = execute_bulk_action(
            self.user_id, action="archive", email_ids=[self.ext_id]
        )
        self.assertEqual(result.get("processed"), 1)
        self.assertGreaterEqual(result.get("workflow_updated", 0), 1)

        row = get_or_create_workflow_state(self.user_id, self.ext_id, provider="gmail")
        self.assertEqual(row["workflow_status"], "archived")
        self.assertEqual(int(row["hidden_from_command_center"] or 0), 1)

        active = list_classified_emails(
            self.user_id, category="business_lead", include_handled=False
        )
        self.assertNotIn(self.ext_id, [e["id"] for e in active.get("emails") or []])
        handled = list_classified_emails(
            self.user_id, category="business_lead", include_handled=True
        )
        self.assertIn(self.ext_id, [e["id"] for e in handled.get("emails") or []])

    @patch("integrations.gmail.gmail_client.gmail_client.get_gmail_service_for_user")
    def test_repeated_archive_idempotent(self, mock_gmail):
        self._seed_lead(self.ext_id)
        gmail_service = MagicMock()
        modify_mock = gmail_service.users.return_value.messages.return_value.modify
        modify_mock.return_value.execute.return_value = {}
        mock_gmail.return_value = gmail_service

        execute_bulk_action(self.user_id, action="archive", email_ids=[self.ext_id])
        self.assertEqual(modify_mock.call_count, 1)
        r2 = execute_bulk_action(self.user_id, action="archive", email_ids=[self.ext_id])
        self.assertEqual(r2.get("processed"), 1)
        self.assertGreaterEqual(r2.get("workflow_skipped", 0), 1)
        self.assertEqual(modify_mock.call_count, 1)

    @patch("integrations.gmail.gmail_client.gmail_client.get_gmail_service_for_user")
    def test_bulk_not_a_lead_dismissed(self, mock_gmail):
        self._seed_lead(self.ext_id)
        result = execute_bulk_action(
            self.user_id, action="not_a_lead", email_ids=[self.ext_id]
        )
        self.assertEqual(result.get("processed"), 1)
        mock_gmail.assert_not_called()
        row = get_or_create_workflow_state(self.user_id, self.ext_id, provider="gmail")
        self.assertEqual(row["workflow_status"], "dismissed")
        active = list_classified_emails(
            self.user_id, category="business_lead", include_handled=False
        )
        self.assertNotIn(self.ext_id, [e["id"] for e in active.get("emails") or []])

    def test_bulk_restore_to_queue_after_dismiss(self):
        self._seed_lead(self.ext_id)
        execute_bulk_action(self.user_id, action="dismiss", email_ids=[self.ext_id])
        dismissed = get_or_create_workflow_state(self.user_id, self.ext_id, provider="gmail")
        self.assertEqual(dismissed["workflow_status"], "dismissed")

        result = execute_bulk_action(
            self.user_id, action="restore_to_queue", email_ids=[self.ext_id]
        )
        self.assertEqual(result.get("processed"), 1)
        restored = get_or_create_workflow_state(self.user_id, self.ext_id, provider="gmail")
        self.assertEqual(restored["workflow_status"], "active")
        self.assertEqual(int(restored.get("hidden_from_command_center") or 0), 0)
        active = list_classified_emails(
            self.user_id, category="business_lead", include_handled=False
        )
        self.assertIn(self.ext_id, [e["id"] for e in active.get("emails") or []])

    @patch("integrations.gmail.gmail_client.gmail_client.get_gmail_service_for_user")
    def test_bulk_spam_and_done_hide(self, mock_gmail):
        ext_spam = "wf-phasec-spam"
        ext_done = "wf-phasec-done"
        self._seed_lead(ext_spam)
        self._seed_lead(ext_done)
        gmail_service = MagicMock()
        gmail_service.users().messages().modify().execute.return_value = {}
        mock_gmail.return_value = gmail_service

        execute_bulk_action(
            self.user_id,
            action="spam_candidate",
            email_ids=[ext_spam],
            confirm_destructive=True,
        )
        execute_bulk_action(self.user_id, action="done", email_ids=[ext_done])

        spam_row = get_or_create_workflow_state(self.user_id, ext_spam, provider="gmail")
        done_row = get_or_create_workflow_state(self.user_id, ext_done, provider="gmail")
        self.assertEqual(spam_row["workflow_status"], "spam")
        self.assertEqual(done_row["workflow_status"], "done")

    @patch(
        "services.email_triage_service._create_lead_from_classified_email",
        return_value=True,
    )
    def test_bulk_create_leads_converted(self, _mock_lead):
        self._seed_lead(self.ext_id)
        result = execute_bulk_action(
            self.user_id, action="create_leads", email_ids=[self.ext_id]
        )
        self.assertEqual(result.get("processed"), 1)
        row = get_or_create_workflow_state(self.user_id, self.ext_id, provider="gmail")
        self.assertEqual(row["workflow_status"], "converted_to_lead")

    @patch("integrations.gmail.gmail_client.gmail_client.get_gmail_service_for_user")
    def test_bulk_partial_failure_workflow_only_successes(self, mock_gmail):
        ext_ok = "wf-phasec-ok"
        ext_fail = "wf-phasec-fail"
        self._seed_lead(ext_ok)
        self._seed_lead(ext_fail)
        gmail_service = MagicMock()

        def _modify_side_effect(*_a, **_k):
            body = _k.get("body") or (_a[2] if len(_a) > 2 else {})
            if isinstance(body, dict) and body.get("removeLabelIds") == ["INBOX"]:
                pass
            return MagicMock()

        modify_chain = gmail_service.users().messages().modify
        call_count = {"n": 0}

        def _modify(**kwargs):
            call_count["n"] += 1
            msg_id = kwargs.get("id")
            if msg_id == ext_fail:
                raise RuntimeError("gmail failed")
            m = MagicMock()
            m.execute.return_value = {}
            return m

        modify_chain.side_effect = _modify
        mock_gmail.return_value = gmail_service

        result = execute_bulk_action(
            self.user_id,
            action="archive",
            email_ids=[ext_ok, ext_fail],
        )
        self.assertEqual(result.get("processed"), 1)
        self.assertEqual(len(result.get("errors") or []), 1)
        ok_row = get_or_create_workflow_state(self.user_id, ext_ok, provider="gmail")
        fail_row = get_or_create_workflow_state(self.user_id, ext_fail, provider="gmail")
        self.assertEqual(ok_row["workflow_status"], "archived")
        self.assertNotEqual(fail_row.get("workflow_status"), "archived")

    @patch("integrations.gmail.gmail_client.gmail_client.get_gmail_service_for_user")
    def test_mark_read_keeps_active_in_command_center(self, mock_gmail):
        self._seed_lead(self.ext_id)
        gmail_service = MagicMock()
        gmail_service.users().messages().modify().execute.return_value = {}
        mock_gmail.return_value = gmail_service

        execute_bulk_action(
            self.user_id, action="mark_read", email_ids=[self.ext_id]
        )
        row = get_or_create_workflow_state(self.user_id, self.ext_id, provider="gmail")
        self.assertEqual(row["workflow_status"], "active")
        self.assertEqual(int(row["hidden_from_command_center"] or 0), 0)
        active = list_classified_emails(
            self.user_id, category="business_lead", include_handled=False
        )
        self.assertIn(self.ext_id, [e["id"] for e in active.get("emails") or []])


def _business_test_client():
    from flask import Flask
    from routes.business import business_bp

    test_app = Flask(__name__)
    test_app.config["TESTING"] = True
    test_app.register_blueprint(business_bp)
    return test_app.test_client()


class TestPhaseCLiveMailArchive(unittest.TestCase):
    def setUp(self):
        ensure_email_workflow_state_table()
        ensure_email_classifications_table()
        self.user_id = _USER_WORKFLOW_BASE + 5
        self.ext_id = "wf-live-archive-001"
        _ensure_workflow_test_user(self.user_id)
        self.client = _business_test_client()

    def tearDown(self):
        _cleanup_workflow_test_user(self.user_id)

    @patch("integrations.gmail.gmail_client.gmail_client")
    @patch("routes.business.get_current_user_id")
    def test_archive_persists_workflow_and_removes_inbox_label(
        self, mock_user, mock_gmail_client
    ):
        mock_user.return_value = self.user_id
        gmail_service = MagicMock()
        gmail_service.users().messages().modify().execute.return_value = {}
        mock_gmail_client.get_gmail_service_for_user.return_value = gmail_service

        _insert_synced_email_row(
            self.user_id,
            self.ext_id,
            subject="Sub",
            labels='["INBOX","UNREAD"]',
        )

        response = self.client.post(
            "/api/email/archive",
            json={"email_id": self.ext_id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        row = get_or_create_workflow_state(self.user_id, self.ext_id, provider="gmail")
        self.assertEqual(row["workflow_status"], "archived")
        synced = db_optimizer.execute_query(
            "SELECT labels FROM synced_emails WHERE user_id = ? AND external_id = ?",
            (self.user_id, self.ext_id),
        )
        labels = json.loads(synced[0]["labels"])
        self.assertNotIn("INBOX", labels)

    @patch("integrations.gmail.gmail_client.gmail_client")
    @patch("routes.business.get_current_user_id")
    def test_archive_succeeds_without_synced_row(self, mock_user, mock_gmail_client):
        mock_user.return_value = self.user_id
        gmail_service = MagicMock()
        gmail_service.users().messages().modify().execute.return_value = {}
        mock_gmail_client.get_gmail_service_for_user.return_value = gmail_service

        response = self.client.post(
            "/api/email/archive",
            json={"email_id": "no-synced-row-msg"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        row = get_or_create_workflow_state(
            self.user_id, "no-synced-row-msg", provider="gmail"
        )
        self.assertEqual(row["workflow_status"], "archived")

    @patch("integrations.gmail.gmail_client.gmail_client")
    @patch("routes.business.get_current_user_id")
    def test_mark_read_updates_synced_but_stays_active(
        self, mock_user, mock_gmail_client
    ):
        mock_user.return_value = self.user_id
        gmail_service = MagicMock()
        gmail_service.users().messages().modify().execute.return_value = {}
        mock_gmail_client.get_gmail_service_for_user.return_value = gmail_service

        ext = "wf-live-read-001"
        upsert_classification(
            self.user_id,
            external_id=ext,
            provider="gmail",
            triage={
                "category": "business_lead",
                "lead_score": 65,
                "business_relevance_score": 65,
                "urgency_score": 40,
                "cleanup_action": "keep",
                "confidence": 0.7,
                "reason": "read test",
            },
        )
        mark_classified(self.user_id, ext, provider="gmail")
        _insert_synced_email_row(
            self.user_id,
            ext,
            subject="Sub",
            labels='["INBOX","UNREAD"]',
        )

        response = self.client.post(
            "/api/email/mark-read",
            json={"email_id": ext},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        synced = db_optimizer.execute_query(
            "SELECT labels, is_read FROM synced_emails WHERE user_id = ? AND external_id = ?",
            (self.user_id, ext),
        )
        labels = json.loads(synced[0]["labels"])
        self.assertNotIn("UNREAD", labels)
        self.assertTrue(synced[0].get("is_read") in (1, True, "1"))

        row = get_or_create_workflow_state(self.user_id, ext, provider="gmail")
        self.assertEqual(row["workflow_status"], "active")
        active = list_classified_emails(
            self.user_id, category="business_lead", include_handled=False
        )
        self.assertIn(ext, [e["id"] for e in active.get("emails") or []])


if __name__ == "__main__":
    unittest.main()
