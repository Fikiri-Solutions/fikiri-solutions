#!/usr/bin/env python3
"""Tests for append-only automation_run_events."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


class TestAutomationRunEvents(unittest.TestCase):
    def tearDown(self):
        import core.automation_run_events as are

        are._table_ensured = False

    def test_record_is_noop_without_run_context(self):
        from core import automation_run_events as are

        are._table_ensured = False
        with patch.object(are.db_optimizer, "execute_query") as mock_ex:
            are.record_automation_run_event(1, "automation.triggered", payload={"x": 1})
            mock_ex.assert_not_called()

    @patch("core.automation_run_events.db_optimizer")
    def test_record_inserts_when_context_set(self, mock_db):
        from core.automation_run_events import (
            automation_run_context,
            record_automation_run_event,
            ensure_automation_run_events_table,
        )

        mock_db.execute_query.return_value = None
        ensure_automation_run_events_table()
        with automation_run_context(run_id="run-1", job_id="job-1", source="test"):
            record_automation_run_event(42, "automation.triggered", payload={"a": 1})
        self.assertTrue(mock_db.execute_query.called)

    @patch("core.automation_run_events.db_optimizer")
    def test_cancel_insert_independent_of_context(self, mock_db):
        from core.automation_run_events import record_automation_cancelled

        mock_db.execute_query.return_value = None
        record_automation_cancelled(7, run_id="j1", job_id="j1", reason="withdrawn", lead_id=99)
        calls = [c[0][0] for c in mock_db.execute_query.call_args_list if c[0]]
        self.assertTrue(any("automation_run_events" in str(c) for c in calls))


if __name__ == "__main__":
    unittest.main()
