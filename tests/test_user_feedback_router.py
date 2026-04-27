#!/usr/bin/env python3
"""
Tests for centralized user feedback router.
"""

import os
import sys
import sqlite3
import unittest
from unittest.mock import patch

os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("SKIP_HEAVY_DEP_CHECKS", "true")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.user_feedback_router import UserFeedbackRouter


class TestUserFeedbackRouter(unittest.TestCase):
    def setUp(self):
        self.router = UserFeedbackRouter()

    @patch("core.user_feedback_router.db_optimizer")
    def test_records_feedback_event_success(self, mock_db):
        mock_db.table_exists.return_value = True
        mock_db.execute_query.return_value = 123

        result = self.router.record_feedback_event(
            source="api.public_chatbot.feedback",
            user_id="42",
            tenant_id="tenant-1",
            category="chatbot",
            conversation_id="conv-1",
            message_id="msg-1",
            correlation_id="corr-1",
            payload={"helpful": True, "feedback_text": "good"},
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["route"], "chatbot.quality")
        self.assertEqual(result["event_id"], 123)
        mock_db.execute_query.assert_called_once()

    @patch("core.user_feedback_router.db_optimizer")
    def test_rejects_invalid_payload(self, mock_db):
        mock_db.table_exists.return_value = True

        result = self.router.record_feedback_event(
            source="api.public_chatbot.feedback",
            user_id=None,
            tenant_id=None,
            category="general",
            payload="not-an-object",
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "INVALID_PAYLOAD")
        mock_db.execute_query.assert_not_called()

    @patch("core.user_feedback_router.db_optimizer")
    def test_retries_locked_database(self, mock_db):
        mock_db.table_exists.return_value = True
        mock_db.execute_query.side_effect = [
            sqlite3.OperationalError("database is locked"),
            sqlite3.OperationalError("database is busy"),
            999,
        ]

        result = self.router.record_feedback_event(
            source="api.chatbot.feedback",
            user_id="10",
            tenant_id="10",
            category="feature_request",
            payload={"title": "Need filters"},
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["route"], "product.feature_request")
        self.assertEqual(mock_db.execute_query.call_count, 3)

    @patch("core.user_feedback_router.db_optimizer")
    def test_uses_explicit_idempotency_key(self, mock_db):
        mock_db.table_exists.return_value = True
        mock_db.execute_query.return_value = 1

        result = self.router.record_feedback_event(
            source="api.expert.feedback",
            user_id="1",
            tenant_id="1",
            category="bug",
            payload={"helpful": False},
            idempotency_key="feedback-abc",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["idempotency_key"], "feedback-abc")
        args, _ = mock_db.execute_query.call_args
        self.assertEqual(args[1][-1], "feedback-abc")


if __name__ == "__main__":
    unittest.main()
