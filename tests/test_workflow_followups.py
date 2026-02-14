#!/usr/bin/env python3
"""Workflow follow-up execution tests."""

import unittest
from unittest.mock import patch, MagicMock

from core import workflow_followups


class _Idem:
    def __init__(self):
        self.store = {}

    def check_key(self, key):
        return self.store.get(key)

    def store_key(self, key, *_args, **_kwargs):
        self.store[key] = {"status": "pending"}

    def update_key_result(self, key, status, response_data=None):
        self.store[key] = {"status": status, "response_data": response_data}


def _db_side_effect(sql, params=None, fetch=True):
    sql_upper = sql.strip().upper()
    if sql_upper.startswith("SELECT ID, USER_ID"):
        # scheduled_follow_ups
        return [{
            "id": 1,
            "user_id": params[0],
            "lead_id": 10,
            "follow_up_date": params[1],
            "follow_up_type": "email",
            "message": "Hello"
        }]
    if "FROM LEADS" in sql_upper:
        return [{"id": 10, "email": "lead@example.com", "name": "Lead"}]
    return None


class TestWorkflowFollowups(unittest.TestCase):
    @patch("core.workflow_followups.automation_safety_manager")
    @patch("core.workflow_followups.enhanced_crm_service")
    @patch("core.workflow_followups._send_email")
    @patch("core.workflow_followups.db_optimizer")
    def test_followup_execution_idempotent(self, mock_db, mock_send, mock_crm, mock_safety):
        mock_db.execute_query.side_effect = _db_side_effect
        mock_send.return_value = {"success": True}
        mock_safety.check_rate_limits.return_value = {"allowed": True}

        idem = _Idem()
        with patch("core.workflow_followups.idempotency_manager", idem):
            first = workflow_followups.execute_due_follow_ups(1, now_iso="2025-01-01T00:00:00")
            second = workflow_followups.execute_due_follow_ups(1, now_iso="2025-01-01T00:00:00")

        self.assertEqual(first.get("processed"), 1)
        self.assertEqual(second.get("processed"), 0)
        self.assertEqual(mock_send.call_count, 1)


if __name__ == '__main__':
    unittest.main()
