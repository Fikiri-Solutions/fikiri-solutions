"""
Unit tests for core/workflow_followups.py (schedule_follow_up, execute_due_follow_ups).
"""

import json
import os
import sys
from unittest.mock import patch, MagicMock

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.workflow_followups import (
    schedule_follow_up,
    execute_due_follow_ups,
    should_skip_scheduled_follow_up_email,
)


class TestScheduleFollowUp:
    @patch("core.workflow_followups.db_optimizer")
    def test_schedule_follow_up_invalid_type_returns_error(self, mock_db):
        result = schedule_follow_up(
            user_id=1,
            lead_id=1,
            follow_up_date="2024-12-01",
            follow_up_type="invalid",
            message="Hi",
        )
        assert result.get("success") is False
        assert "Invalid" in result.get("error", "")

    @patch("core.workflow_followups.db_optimizer")
    def test_schedule_follow_up_email_dedup_returns_success(self, mock_db):
        mock_db.execute_query.side_effect = [
            [{"id": 99}],  # existing
        ]
        result = schedule_follow_up(
            user_id=1,
            lead_id=1,
            follow_up_date="2024-12-01",
            follow_up_type="email",
            message="Hi",
        )
        assert result.get("success") is True
        assert result.get("follow_up_id") == 99
        assert result.get("deduped") is True
        dedup_sql = mock_db.execute_query.call_args_list[0][0][0]
        assert "lead_id = ?" in dedup_sql
        assert "lead_id IS ?" not in dedup_sql

    @patch("core.workflow_followups.db_optimizer")
    def test_schedule_follow_up_null_lead_dedup_uses_is_null(self, mock_db):
        mock_db.execute_query.return_value = []
        schedule_follow_up(
            user_id=1,
            lead_id=None,
            follow_up_date="2024-12-01",
            follow_up_type="email",
            message="Hi",
        )
        dedup_sql = mock_db.execute_query.call_args_list[0][0][0]
        assert "lead_id IS NULL" in dedup_sql

    @patch("core.workflow_followups.db_optimizer")
    def test_schedule_follow_up_email_new_returns_success(self, mock_db):
        mock_db.execute_query.side_effect = [
            [],  # no existing
        ]
        mock_db.execute_insert_returning_id.return_value = 42
        result = schedule_follow_up(
            user_id=1,
            lead_id=None,
            follow_up_date="2024-12-01",
            follow_up_type="email",
            message="Hi",
        )
        assert result.get("success") is True
        assert result.get("follow_up_id") == 42
        assert result.get("deduped") is False


class TestCancelPendingWorkForLead:
    @patch("core.workflow_followups.record_automation_cancelled")
    @patch("core.workflow_followups.db_optimizer")
    def test_cancel_matching_automation_job_records_event(self, mock_db, mock_cancel):
        def se(*args, **kwargs):
            q = args[0] if args else ""
            if "FROM scheduled_follow_ups" in q and "SELECT id" in q:
                return []
            if "UPDATE scheduled_follow_ups" in q:
                return 0
            if "UPDATE follow_up_tasks" in q:
                return 0
            if "FROM automation_jobs" in q:
                return [
                    {
                        "job_id": "automation_abc",
                        "payload_json": json.dumps({"trigger_data": {"lead_id": 9}}),
                        "status": "queued",
                    }
                ]
            if "UPDATE automation_jobs" in q:
                return 0
            if "UPDATE calendar_events" in q:
                return 0
            return None

        mock_db.execute_query.side_effect = se
        from core.workflow_followups import cancel_pending_work_for_lead

        cancel_pending_work_for_lead(1, 9, reason="test_reason")
        mock_cancel.assert_called_once_with(
            1,
            run_id="automation_abc",
            job_id="automation_abc",
            reason="test_reason",
            lead_id=9,
        )


class TestShouldSkipScheduledFollowUpEmail:
    def test_reserved_domains_skipped(self):
        for addr in (
            "a@example.com",
            "x@example.org",
            "u@example.test",
            "u@foo.invalid",
        ):
            skip, reason = should_skip_scheduled_follow_up_email(addr)
            assert skip, addr
            assert reason == "reserved_recipient_domain"

    def test_automated_and_newsletter_senders_skipped(self):
        cases = (
            ("noreply@github.com", "automated_sender"),
            ("notifications@github.com", "automated_sender"),
            ("workspace-noreply@google.com", "automated_sender"),
            ("newsletter@email.hihello.com", "newsletter_sender"),
            ("news@llamaindex.ai", "newsletter_sender"),
            ("community@trypinecone.com", "newsletter_sender"),
        )
        for addr, expected_reason in cases:
            skip, reason = should_skip_scheduled_follow_up_email(addr)
            assert skip, addr
            assert reason == expected_reason

    def test_real_lead_not_skipped(self):
        skip, reason = should_skip_scheduled_follow_up_email("pat.smith@acmecorp.com")
        assert skip is False
        assert reason == ""


class TestExecuteDueFollowUps:
    @patch("core.workflow_followups.db_optimizer")
    def test_execute_due_follow_ups_empty_list_returns_counts(self, mock_db):
        mock_db.execute_query.return_value = []
        result = execute_due_follow_ups(user_id=1)
        assert "processed" in result
        assert "failed" in result
        assert result["processed"] == 0
        assert result["failed"] == 0

    @patch("core.workflow_followups._send_sms")
    @patch("core.workflow_followups.automation_safety_manager")
    @patch("core.workflow_followups.idempotency_manager")
    @patch("core.workflow_followups.db_optimizer")
    def test_sms_follow_up_blocked_without_consent(
        self, mock_db, mock_idem, mock_safety, mock_send_sms
    ):
        mock_idem.check_key.return_value = None
        mock_idem.store_key = MagicMock()
        mock_idem.update_key_result = MagicMock()
        mock_safety.check_rate_limits.return_value = {"allowed": True}
        mock_safety.log_automation_action = MagicMock()

        def q_side(sql, params=None, fetch=True, **kwargs):
            s = (sql or "").upper()
            if "FROM SCHEDULED_FOLLOW_UPS" in s and "WHERE USER_ID" in s:
                return [
                    {
                        "id": 10,
                        "user_id": 1,
                        "lead_id": 5,
                        "follow_up_date": "2000-01-01T00:00:00",
                        "follow_up_type": "sms",
                        "message": "Hi",
                    }
                ]
            if "FROM LEADS" in s and "METADATA" in s:
                return [{"id": 5, "phone": "+15551234567", "metadata": "{}"}]
            if "INSERT INTO SMS_MESSAGES" in s:
                return None
            if "UPDATE SCHEDULED_FOLLOW_UPS" in s:
                return None
            return []

        mock_db.execute_query.side_effect = q_side
        mock_db.execute_insert_returning_id = MagicMock()

        result = execute_due_follow_ups(user_id=1)
        mock_send_sms.assert_not_called()
        assert result["failed"] >= 1

    @patch("core.workflow_followups._send_sms")
    @patch("core.workflow_followups.automation_safety_manager")
    @patch("core.workflow_followups.idempotency_manager")
    @patch("core.workflow_followups.db_optimizer")
    def test_sms_follow_up_sends_when_consent_true(
        self, mock_db, mock_idem, mock_safety, mock_send_sms
    ):
        mock_idem.check_key.return_value = None
        mock_idem.store_key = MagicMock()
        mock_idem.update_key_result = MagicMock()
        mock_safety.check_rate_limits.return_value = {"allowed": True}
        mock_safety.log_automation_action = MagicMock()
        mock_send_sms.return_value = {"success": True}

        consent_meta = '{"sms_consent": true, "sms_consent_at": "2026-01-01T00:00:00Z"}'

        def q_side(sql, params=None, fetch=True, **kwargs):
            s = (sql or "").upper()
            if "FROM SCHEDULED_FOLLOW_UPS" in s and "WHERE USER_ID" in s:
                return [
                    {
                        "id": 11,
                        "user_id": 1,
                        "lead_id": 6,
                        "follow_up_date": "2000-01-01T00:00:00",
                        "follow_up_type": "sms",
                        "message": "Hi",
                    }
                ]
            if "FROM LEADS" in s and "METADATA" in s:
                return [{"id": 6, "phone": "+15551234567", "metadata": consent_meta}]
            if "INSERT INTO SMS_MESSAGES" in s:
                return None
            if "UPDATE SCHEDULED_FOLLOW_UPS" in s:
                return None
            return []

        mock_db.execute_query.side_effect = q_side

        result = execute_due_follow_ups(user_id=1)
        mock_send_sms.assert_called_once()
        assert result["processed"] >= 1

    @patch("core.workflow_followups._send_email")
    @patch("core.workflow_followups.automation_safety_manager")
    @patch("core.workflow_followups.idempotency_manager")
    @patch("core.workflow_followups.db_optimizer")
    def test_email_follow_up_skips_noreply_without_gmail_send(
        self, mock_db, mock_idem, mock_safety, mock_send_email
    ):
        mock_idem.check_key.return_value = None
        mock_idem.store_key = MagicMock()
        mock_idem.update_key_result = MagicMock()
        mock_safety.check_rate_limits.return_value = {"allowed": True}
        mock_safety.log_automation_action = MagicMock()
        update_calls = []

        def q_side(sql, params=None, fetch=True, **kwargs):
            s = (sql or "").upper()
            if "FROM SCHEDULED_FOLLOW_UPS" in s and "WHERE USER_ID" in s:
                return [
                    {
                        "id": 20,
                        "user_id": 1,
                        "lead_id": 8,
                        "follow_up_date": "2000-01-01T00:00:00",
                        "follow_up_type": "email",
                        "message": "Hi",
                    }
                ]
            if "FROM LEADS" in s and "EMAIL" in s:
                return [{"id": 8, "email": "notifications@github.com", "name": "GitHub"}]
            if "UPDATE SCHEDULED_FOLLOW_UPS" in s:
                update_calls.append(params)
                return None
            return []

        mock_db.execute_query.side_effect = q_side

        result = execute_due_follow_ups(user_id=1)
        mock_send_email.assert_not_called()
        assert result["processed"] == 0
        assert result["failed"] == 0
        assert update_calls
        assert update_calls[0][0] == "cancelled"
        mock_idem.update_key_result.assert_called_once()
        assert mock_idem.update_key_result.call_args[0][1] == "completed"
        mock_safety.log_automation_action.assert_called_once()
        assert mock_safety.log_automation_action.call_args.kwargs.get("status") == "skipped"

    @patch("core.workflow_followups._send_email")
    @patch("core.workflow_followups.automation_safety_manager")
    @patch("core.workflow_followups.idempotency_manager")
    @patch("core.workflow_followups.db_optimizer")
    def test_email_follow_up_skips_example_com(
        self, mock_db, mock_idem, mock_safety, mock_send_email
    ):
        mock_idem.check_key.return_value = None
        mock_idem.store_key = MagicMock()
        mock_idem.update_key_result = MagicMock()
        mock_safety.log_automation_action = MagicMock()

        def q_side(sql, params=None, fetch=True, **kwargs):
            s = (sql or "").upper()
            if "FROM SCHEDULED_FOLLOW_UPS" in s and "WHERE USER_ID" in s:
                return [
                    {
                        "id": 21,
                        "user_id": 1,
                        "lead_id": 9,
                        "follow_up_date": "2000-01-01T00:00:00",
                        "follow_up_type": "email",
                        "message": "Hi",
                    }
                ]
            if "FROM LEADS" in s and "EMAIL" in s:
                return [{"id": 9, "email": "lead@example.com", "name": "Test"}]
            if "UPDATE SCHEDULED_FOLLOW_UPS" in s:
                return None
            return []

        mock_db.execute_query.side_effect = q_side
        execute_due_follow_ups(user_id=1)
        mock_send_email.assert_not_called()

    @patch("core.workflow_followups._send_email")
    @patch("core.workflow_followups.enhanced_crm_service")
    @patch("core.workflow_followups.automation_safety_manager")
    @patch("core.workflow_followups.idempotency_manager")
    @patch("core.workflow_followups.db_optimizer")
    def test_email_follow_up_sends_valid_recipient(
        self, mock_db, mock_idem, mock_safety, mock_crm, mock_send_email
    ):
        mock_idem.check_key.return_value = None
        mock_idem.store_key = MagicMock()
        mock_idem.update_key_result = MagicMock()
        mock_safety.check_rate_limits.return_value = {"allowed": True}
        mock_safety.log_automation_action = MagicMock()
        mock_send_email.return_value = {
            "success": True,
            "message_id": "gm-1",
            "channel": "gmail",
        }
        update_calls = []

        def q_side(sql, params=None, fetch=True, **kwargs):
            s = (sql or "").upper()
            if "FROM SCHEDULED_FOLLOW_UPS" in s and "WHERE USER_ID" in s:
                return [
                    {
                        "id": 22,
                        "user_id": 1,
                        "lead_id": 10,
                        "follow_up_date": "2000-01-01T00:00:00",
                        "follow_up_type": "email",
                        "message": "Hi",
                    }
                ]
            if "FROM LEADS" in s and "EMAIL" in s:
                return [{"id": 10, "email": "real.lead@acmecorp.com", "name": "Pat"}]
            if "UPDATE SCHEDULED_FOLLOW_UPS" in s:
                update_calls.append(params)
                return None
            return []

        mock_db.execute_query.side_effect = q_side

        result = execute_due_follow_ups(user_id=1)
        mock_send_email.assert_called_once_with(
            1, "real.lead@acmecorp.com", "Follow-up", "Hi"
        )
        assert result["processed"] == 1
        assert update_calls[0][0] == "sent"
        mock_crm.add_lead_activity.assert_called_once()

    @patch("core.workflow_followups._send_email")
    @patch("core.workflow_followups.automation_safety_manager")
    @patch("core.workflow_followups.idempotency_manager")
    @patch("core.workflow_followups.db_optimizer")
    def test_skipped_follow_up_not_retried_on_second_run(
        self, mock_db, mock_idem, mock_safety, mock_send_email
    ):
        mock_idem.check_key.return_value = {"status": "completed", "result": {"skipped": True}}
        mock_idem.store_key = MagicMock()
        mock_safety.log_automation_action = MagicMock()

        def q_side(sql, params=None, fetch=True, **kwargs):
            s = (sql or "").upper()
            if "FROM SCHEDULED_FOLLOW_UPS" in s and "WHERE USER_ID" in s:
                return [
                    {
                        "id": 23,
                        "user_id": 1,
                        "lead_id": 11,
                        "follow_up_date": "2000-01-01T00:00:00",
                        "follow_up_type": "email",
                        "message": "Hi",
                    }
                ]
            return []

        mock_db.execute_query.side_effect = q_side
        result = execute_due_follow_ups(user_id=1)
        mock_send_email.assert_not_called()
        assert result["processed"] == 0
        assert result["failed"] == 0

    @patch("core.workflow_followups._send_email")
    @patch("core.workflow_followups.automation_safety_manager")
    @patch("core.workflow_followups.idempotency_manager")
    @patch("core.workflow_followups.db_optimizer")
    def test_scheduler_continues_after_skipped_recipient(
        self, mock_db, mock_idem, mock_safety, mock_send_email
    ):
        mock_idem.check_key.return_value = None
        mock_idem.store_key = MagicMock()
        mock_idem.update_key_result = MagicMock()
        mock_safety.check_rate_limits.return_value = {"allowed": True}
        mock_safety.log_automation_action = MagicMock()
        mock_send_email.return_value = {"success": True, "message_id": "gm-2", "channel": "gmail"}

        def q_side(sql, params=None, fetch=True, **kwargs):
            s = (sql or "").upper()
            if "FROM SCHEDULED_FOLLOW_UPS" in s and "WHERE USER_ID" in s:
                return [
                    {
                        "id": 24,
                        "user_id": 1,
                        "lead_id": 12,
                        "follow_up_date": "2000-01-01T00:00:00",
                        "follow_up_type": "email",
                        "message": "A",
                    },
                    {
                        "id": 25,
                        "user_id": 1,
                        "lead_id": 13,
                        "follow_up_date": "2000-01-01T00:00:00",
                        "follow_up_type": "email",
                        "message": "B",
                    },
                ]
            if "FROM LEADS" in s and "EMAIL" in s:
                lead_id = params[0] if params else None
                if lead_id == 12:
                    return [{"id": 12, "email": "newsletter@vendor.com", "name": "V"}]
                if lead_id == 13:
                    return [{"id": 13, "email": "buyer@realco.com", "name": "Buyer"}]
            if "UPDATE SCHEDULED_FOLLOW_UPS" in s:
                return None
            return []

        mock_db.execute_query.side_effect = q_side

        result = execute_due_follow_ups(user_id=1)
        mock_send_email.assert_called_once_with(1, "buyer@realco.com", "Follow-up", "B")
        assert result["processed"] == 1
        assert mock_idem.update_key_result.call_count == 2
