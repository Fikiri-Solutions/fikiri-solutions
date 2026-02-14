#!/usr/bin/env python3
"""
Follow-up System Unit Tests
Tests for email_automation/followup_system.py
"""

import unittest
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("FIKIRI_TEST_MODE", "1")

from email_automation.followup_system import AutomatedFollowUpSystem, FollowUpTemplate


class _Token:
    def __init__(self, access_token="token"):
        self.access_token = access_token


class _FakeClient:
    def is_enabled(self):
        return True


class _FakeRouter:
    def __init__(self, content):
        self.client = _FakeClient()
        self._content = content

    def process(self, **_kwargs):
        return {"success": True, "content": self._content}


class TestFollowUpSystem(unittest.TestCase):
    def setUp(self):
        self.system = AutomatedFollowUpSystem()
        self.system.email_handler = MagicMock()

    @patch("email_automation.followup_system.db_optimizer")
    def test_create_follow_up_task_success(self, mock_db):
        mock_db.execute_query.return_value = None
        result = self.system.create_follow_up_task(lead_id="l1", user_id=7, stage="new")
        self.assertTrue(result.get("success"))
        self.assertIn("task_id", result)
        mock_db.execute_query.assert_called_once()

    def test_prepare_email_content_fallback(self):
        self.system.router = None
        template = self.system.default_templates[0]
        task_data = {
            "name": "Alex",
            "company": "Acme",
            "stage": "new",
            "meta": '{"service_type": "consulting"}',
        }
        content = self.system._prepare_email_content(template, task_data)
        self.assertIn("Acme", content["subject"])
        self.assertIn("consulting", content["body"])

    def test_prepare_email_content_llm_success(self):
        self.system.router = _FakeRouter('{"subject": "Hi", "body": "Hello"}')
        template = self.system.default_templates[0]
        content = self.system._prepare_email_content(template, {"meta": "{}"})
        self.assertEqual(content["subject"], "Hi")
        self.assertEqual(content["body"], "Hello")

    @patch("email_automation.followup_system.db_optimizer")
    def test_process_pending_follow_ups_counts(self, mock_db):
        mock_db.execute_query.return_value = [
            {"id": "t1", "lead_id": "l1", "template_id": "initial_contact", "user_id": 1},
            {"id": "t2", "lead_id": "l2", "template_id": "initial_contact", "user_id": 1},
        ]

        self.system._send_follow_up = MagicMock(side_effect=[{"success": True}, {"success": False}])
        self.system._update_task_status = MagicMock()

        result = self.system.process_pending_follow_ups()

        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("processed"), 1)
        self.assertEqual(result.get("failed"), 1)
        self.assertEqual(self.system._update_task_status.call_count, 2)

    @patch("email_automation.followup_system.gmail_oauth_manager")
    def test_send_follow_up_success(self, mock_gmail):
        mock_gmail.get_user_tokens.return_value = _Token()
        self.system.email_handler.send_ai_response.return_value = {"success": True}
        self.system._log_follow_up_activity = MagicMock()
        self.system._prepare_email_content = MagicMock(return_value={"subject": "S", "body": "B"})

        task_data = {
            "id": "t1",
            "lead_id": "l1",
            "template_id": "initial_contact",
            "user_id": 2,
            "meta": "{}",
        }

        result = self.system._send_follow_up(task_data)
        self.assertTrue(result.get("success"))
        self.system._log_follow_up_activity.assert_called_once()

    def test_send_follow_up_idempotent(self):
        class _Idem:
            def __init__(self):
                self.cached = None

            def generate_key(self, *_args, **_kwargs):
                return "k1"

            def check_key(self, _key):
                return self.cached

            def store_key(self, *_args, **_kwargs):
                return True

            def update_key_result(self, _key, _status, response_data=None):
                self.cached = {"status": "completed", "response_data": response_data}
                return True

        self.system.email_handler.send_ai_response = MagicMock(return_value={"success": True})
        self.system._log_follow_up_activity = MagicMock()
        self.system._prepare_email_content = MagicMock(return_value={"subject": "S", "body": "B"})

        task_data = {
            "id": "t1",
            "lead_id": "l1",
            "template_id": "initial_contact",
            "user_id": 2,
            "meta": "{}",
        }

        with patch("email_automation.followup_system.idempotency_manager", new=_Idem()), \
             patch("email_automation.followup_system.gmail_oauth_manager") as mock_gmail:
            mock_gmail.get_user_tokens.return_value = _Token()
            result1 = self.system._send_follow_up(task_data)
            result2 = self.system._send_follow_up(task_data)

        self.assertTrue(result1.get("success"))
        self.assertTrue(result2.get("success"))
        self.assertEqual(self.system.email_handler.send_ai_response.call_count, 1)


if __name__ == "__main__":
    unittest.main()
