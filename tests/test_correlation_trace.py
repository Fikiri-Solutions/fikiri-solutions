#!/usr/bin/env python3
"""Tests for core.correlation_trace.fetch_correlation_trace."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


class TestCorrelationTrace(unittest.TestCase):
    def test_invalid_correlation_id(self):
        from core.correlation_trace import fetch_correlation_trace

        out = fetch_correlation_trace(1, "")
        self.assertEqual(out.get("error"), "invalid_correlation_id")

    @patch("core.correlation_trace.db_optimizer")
    def test_fetches_sections(self, mock_db):
        mock_db.json_field_expr.return_value = "json_extract(payload_json, '$.correlation_id')"
        mock_db.execute_query.return_value = [{"id": 1, "event_type": "lead.created"}]
        from core.correlation_trace import fetch_correlation_trace

        out = fetch_correlation_trace(7, "abc-123-def")
        self.assertEqual(out["correlation_id"], "abc-123-def")
        self.assertEqual(out["user_id"], 7)
        self.assertIn("crm_events", out["sections"])
        self.assertEqual(len(out["sections"]["crm_events"]), 1)


if __name__ == "__main__":
    unittest.main()
