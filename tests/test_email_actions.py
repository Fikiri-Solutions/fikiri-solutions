#!/usr/bin/env python3
"""
Email Actions Unit Tests
Tests for email_automation/actions.py
"""

import unittest
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


class TestMinimalEmailActions(unittest.TestCase):
    def setUp(self):
        with patch("email_automation.actions.MinimalEmailActions._initialize_database"):
            from email_automation.actions import MinimalEmailActions
            self.actions = MinimalEmailActions(services={})
            self.actions.db_optimizer = MagicMock()

        self.sample_email = {
            "message_id": "m1",
            "headers": {
                "from": "John Doe <john@example.com>",
                "subject": "Need help with service",
                "to": "info@fikirisolutions.com",
            },
            "labels": ["UNREAD", "INBOX"],
            "snippet": "Hi there",
        }

    def test_unknown_action_type(self):
        result = self.actions.process_email(self.sample_email, action_type="nope", user_id=1)
        self.assertFalse(result.get("success"))
        self.assertIn("Unknown action type", result.get("details", {}).get("error", ""))

    def test_template_reply_selection(self):
        support = self.actions._generate_template_reply("John", "Support needed")
        self.assertIn("support team", support.lower())
        lead = self.actions._generate_template_reply("John", "Need a quote")
        self.assertIn("interest in our services", lead.lower())
        general = self.actions._generate_template_reply("John", "Hello")
        self.assertIn("thank you for your email", general.lower())

    def test_extract_name_from_email(self):
        self.assertEqual(self.actions._extract_name_from_email("Jane Doe <jane@x.com>"), "Jane Doe")
        self.assertEqual(self.actions._extract_name_from_email("john.doe@x.com"), "John Doe")
        self.assertEqual(self.actions._extract_name_from_email(""), "Valued Customer")

    def test_auto_reply_uses_ai_assistant_if_available(self):
        ai = MagicMock(generate_reply=MagicMock(return_value="AI reply"))
        self.actions.services["ai_assistant"] = ai
        result = self.actions.process_email(self.sample_email, action_type="auto_reply", user_id=1)
        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("details", {}).get("reply_content"), "AI reply")

    def test_process_email_idempotent(self):
        self.actions._auto_reply = MagicMock(return_value={"success": True, "action": "auto_reply"})
        cached = {
            "status": "completed",
            "response_data": {"success": True, "action": "auto_reply", "message_id": "m1"}
        }
        with patch("email_automation.actions.idempotency_manager") as mock_idem, \
             patch("email_automation.actions.automation_safety_manager") as mock_safety:
            mock_idem.check_key.side_effect = [None, cached]
            mock_safety.check_rate_limits.return_value = {"allowed": True}
            first = self.actions.process_email(self.sample_email, action_type="auto_reply", user_id=1)
            second = self.actions.process_email(self.sample_email, action_type="auto_reply", user_id=1)

        self.assertTrue(first.get("success"))
        self.assertTrue(second.get("success"))
        self.assertEqual(self.actions._auto_reply.call_count, 1)

    def test_gmail_failure_classified_retryable(self):
        class _Resp:
            status = 429

        class _Err(Exception):
            resp = _Resp()

        gmail = MagicMock()
        gmail.users.return_value.messages.return_value.modify.return_value.execute.side_effect = _Err("rate limited")
        self.actions.gmail_service = gmail

        with patch("email_automation.actions.idempotency_manager") as mock_idem, \
             patch("email_automation.actions.automation_safety_manager") as mock_safety:
            mock_idem.check_key.return_value = None
            mock_safety.check_rate_limits.return_value = {"allowed": True}
            result = self.actions.process_email(self.sample_email, action_type="mark_read", user_id=1)

        self.assertFalse(result.get("success"))
        classification = result.get("details", {}).get("error_classification", {})
        self.assertTrue(classification.get("retryable"))

    def test_persist_action_log_called(self):
        self.actions.db_optimizer.execute_query.return_value = None
        result = self.actions.process_email(self.sample_email, action_type="mark_read", user_id=1)
        self.assertTrue(result.get("success"))
        self.actions.db_optimizer.execute_query.assert_called()

    def test_process_email_invalid_parsed(self):
        result = self.actions.process_email(None, action_type="mark_read", user_id=1)
        self.assertFalse(result.get("success"))
        self.assertEqual(
            result.get("details", {}).get("error"), "invalid_parsed_email"
        )

    def test_process_email_malformed_headers_does_not_crash(self):
        bad = {
            "message_id": "m1",
            "headers": "not-a-dict",
            "snippet": "x",
        }
        with patch("email_automation.actions.idempotency_manager") as mock_idem, \
             patch("email_automation.actions.automation_safety_manager") as mock_safety:
            mock_idem.check_key.return_value = None
            mock_safety.check_rate_limits.return_value = {"allowed": True}
            result = self.actions.process_email(bad, action_type="mark_read", user_id=1)
        self.assertIsInstance(result, dict)

    def test_process_email_safety_non_dict_blocked(self):
        with patch("email_automation.actions.idempotency_manager") as mock_idem, \
             patch("email_automation.actions.automation_safety_manager") as mock_safety:
            mock_idem.check_key.return_value = None
            mock_safety.check_rate_limits.return_value = "broken"
            result = self.actions.process_email(
                self.sample_email, action_type="mark_read", user_id=1
            )
        self.assertFalse(result.get("success"))
        self.assertEqual(
            result.get("details", {}).get("error"), "safety_blocked"
        )
        self.assertEqual(result.get("details", {}).get("raw"), "broken")

    def test_process_email_idempotent_normalizes_non_dict_cache(self):
        cached = {
            "status": "completed",
            "response_data": "not-a-dict",
        }
        with patch("email_automation.actions.idempotency_manager") as mock_idem, \
             patch("email_automation.actions.automation_safety_manager") as mock_safety:
            mock_idem.check_key.side_effect = [None, cached]
            mock_safety.check_rate_limits.return_value = {"allowed": True}
            self.actions._mark_read = MagicMock(
                return_value={"success": True, "action": "mark_read"}
            )
            self.actions.process_email(self.sample_email, action_type="mark_read", user_id=1)
            second = self.actions.process_email(
                self.sample_email, action_type="mark_read", user_id=1
            )
        self.assertTrue(second.get("success"))
        self.assertTrue(second.get("details", {}).get("idempotent"))

    def test_process_email_handler_non_dict_normalized(self):
        with patch("email_automation.actions.idempotency_manager") as mock_idem, \
             patch("email_automation.actions.automation_safety_manager") as mock_safety:
            mock_idem.check_key.return_value = None
            mock_safety.check_rate_limits.return_value = {"allowed": True}
            self.actions._mark_read = MagicMock(return_value="bad-handler")
            result = self.actions.process_email(
                self.sample_email, action_type="mark_read", user_id=1
            )
        self.assertFalse(result.get("success"))
        self.assertEqual(
            result.get("details", {}).get("error"), "handler_returned_non_dict"
        )


if __name__ == "__main__":
    unittest.main()
