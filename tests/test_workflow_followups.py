"""
Unit tests for core/workflow_followups.py (schedule_follow_up, execute_due_follow_ups).
"""

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
            42,  # insert returns id
        ]
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


class TestExecuteDueFollowUps:
    @patch("core.workflow_followups.db_optimizer")
    def test_execute_due_follow_ups_empty_list_returns_counts(self, mock_db):
        mock_db.execute_query.return_value = []
        result = execute_due_follow_ups(user_id=1)
        assert "processed" in result
        assert "failed" in result
        assert result["processed"] == 0
        assert result["failed"] == 0
