"""
Unit tests for core/workflow_followups.py (schedule_follow_up, execute_due_follow_ups).
"""

import json
import os
import sys
from unittest.mock import patch, MagicMock

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.workflow_followups import schedule_follow_up, execute_due_follow_ups


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
