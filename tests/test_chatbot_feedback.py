#!/usr/bin/env python3
"""
Tests for POST /api/chatbot/feedback (chatbot_feedback table and rating validation).
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("SKIP_HEAVY_DEP_CHECKS", "true")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from core.chatbot_smart_faq_api import chatbot_bp


class TestChatbotFeedbackEndpoint(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(chatbot_bp)
        self.client = self.app.test_client()

    @patch("core.chatbot_smart_faq_api.db_optimizer")
    @patch("core.chatbot_smart_faq_api.get_current_user_id")
    def test_feedback_success_minimal(self, mock_user_id, mock_db):
        mock_user_id.return_value = None
        mock_db.table_exists.return_value = True
        mock_db.execute_query.return_value = None

        resp = self.client.post(
            "/api/chatbot/feedback",
            json={
                "question": "What are your hours?",
                "answer": "We are open 9-5.",
                "retrieved_doc_ids": ["doc1", "doc2"],
                "rating": "correct",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data.get("success"))
        self.assertIn("message", data)
        mock_db.execute_query.assert_called_once()
        args, _ = mock_db.execute_query.call_args
        params = args[1]
        self.assertEqual(params[2], "What are your hours?")
        self.assertEqual(params[3], "We are open 9-5.")
        self.assertEqual(params[5], "correct")

    @patch("core.chatbot_smart_faq_api.db_optimizer")
    @patch("core.chatbot_smart_faq_api.get_current_user_id")
    def test_feedback_success_with_optional_fields(self, mock_user_id, mock_db):
        mock_user_id.return_value = 42
        mock_db.table_exists.return_value = True
        mock_db.execute_query.return_value = None

        resp = self.client.post(
            "/api/chatbot/feedback",
            json={
                "question": "Q",
                "answer": "A",
                "retrieved_doc_ids": [],
                "rating": "somewhat_incorrect",
                "session_id": "sess-123",
                "metadata": {"source": "widget"},
                "prompt_version": "v1",
                "retriever_version": "v2",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        args, _ = mock_db.execute_query.call_args
        params = args[1]
        self.assertEqual(params[0], 42)
        self.assertEqual(params[1], "sess-123")
        self.assertEqual(params[5], "somewhat_incorrect")

    def test_feedback_rejects_missing_question(self):
        resp = self.client.post(
            "/api/chatbot/feedback",
            json={"answer": "A", "retrieved_doc_ids": [], "rating": "correct"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertFalse(data.get("success", True))
        self.assertEqual(data.get("code"), "MISSING_QUESTION")

    def test_feedback_rejects_missing_answer(self):
        resp = self.client.post(
            "/api/chatbot/feedback",
            json={"question": "Q", "retrieved_doc_ids": [], "rating": "correct"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertEqual(data.get("code"), "MISSING_ANSWER")

    def test_feedback_rejects_invalid_rating(self):
        resp = self.client.post(
            "/api/chatbot/feedback",
            json={
                "question": "Q",
                "answer": "A",
                "retrieved_doc_ids": [],
                "rating": "invalid_rating",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertEqual(data.get("code"), "INVALID_RATING")

    def test_feedback_accepts_all_rating_values(self):
        ratings = ["correct", "somewhat_correct", "somewhat_incorrect", "incorrect"]
        with patch("core.chatbot_smart_faq_api.db_optimizer") as mock_db:
            mock_db.table_exists.return_value = True
            mock_db.execute_query.return_value = None
            with patch("core.chatbot_smart_faq_api.get_current_user_id", return_value=None):
                for rating in ratings:
                    resp = self.client.post(
                        "/api/chatbot/feedback",
                        json={
                            "question": "Q",
                            "answer": "A",
                            "retrieved_doc_ids": [],
                            "rating": rating,
                        },
                        content_type="application/json",
                    )
                    self.assertEqual(resp.status_code, 200, f"rating={rating}")


if __name__ == "__main__":
    unittest.main()
