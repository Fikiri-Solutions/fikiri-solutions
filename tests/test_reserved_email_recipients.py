#!/usr/bin/env python3
"""Regression: reserved documentation/test domains skip real Gmail delivery."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestShouldSkipRealEmailDelivery(unittest.TestCase):
    def test_reserved_domains(self):
        from core.reserved_email_recipients import should_skip_real_email_delivery

        for addr in (
            "a@example.com",
            "lead@example.net",
            "x@example.org",
            "u@example.test",
            "u@example.invalid",
            "u@test.invalid",
            "u@foo.test",
            "u@bar.invalid",
            "local@localhost",
        ):
            with self.subTest(addr=addr):
                self.assertTrue(should_skip_real_email_delivery(addr))

    def test_real_recipients_not_skipped(self):
        from core.reserved_email_recipients import should_skip_real_email_delivery

        self.assertFalse(should_skip_real_email_delivery("user@gmail.com"))
        self.assertFalse(should_skip_real_email_delivery("pat@acme.co"))
        self.assertFalse(should_skip_real_email_delivery(""))
        self.assertFalse(should_skip_real_email_delivery("not-an-email"))


class TestGmailClientSkip(unittest.TestCase):
    @patch("integrations.gmail.gmail_client.GmailClient.get_gmail_service_for_user")
    def test_send_plain_text_skips_reserved_without_api_call(self, mock_svc):
        from integrations.gmail.gmail_client import GmailClient

        client = GmailClient()
        out = client.send_plain_text_as_user(1, "a@example.com", "Subj", "Body")

        self.assertTrue(out.get("success"))
        self.assertTrue(out.get("skipped"))
        self.assertEqual(out.get("reason"), "reserved_recipient_domain")
        mock_svc.assert_not_called()

    @patch("integrations.gmail.gmail_client.GmailClient.get_gmail_service_for_user")
    def test_send_plain_text_calls_gmail_for_real_recipient(self, mock_svc):
        from integrations.gmail.gmail_client import GmailClient

        mock_service = MagicMock()
        mock_service.users().messages().send().execute.return_value = {
            "id": "msg-1",
            "threadId": "t-1",
        }
        mock_svc.return_value = mock_service

        client = GmailClient()
        out = client.send_plain_text_as_user(2, "real.user@gmail.com", "Hi", "Hello")

        self.assertTrue(out.get("success"))
        self.assertFalse(out.get("skipped"))
        mock_svc.assert_called_once()


class TestAutomationSendEmailSkip(unittest.TestCase):
    @patch("services.automation_actions.email_action.gmail_client")
    @patch("services.automation_actions.email_action.send_plain_text_transactional")
    @patch("services.automation_actions.email_action.automation_safety_manager")
    def test_execute_send_email_skips_example_com(
        self, mock_safety, mock_txn, mock_gmail
    ):
        from services.automation_actions.email_action import EmailActionHandler

        handler = EmailActionHandler(MagicMock())
        mock_safety.check_rate_limits.return_value = {"allowed": True}

        out = handler.execute_send_email(
            {"subject": "Hi", "body": "Body"},
            {"sender_email": "lead@example.com", "_automation_rule_id": 3},
            10,
        )

        self.assertTrue(out.get("success"))
        self.assertTrue(out.get("data", {}).get("skipped"))
        mock_gmail.send_plain_text_as_user.assert_not_called()
        mock_txn.assert_not_called()
        mock_safety.log_automation_action.assert_called_once()
        self.assertEqual(
            mock_safety.log_automation_action.call_args.kwargs.get("status"), "skipped"
        )

    @patch("services.automation_actions.email_action.gmail_client")
    @patch("services.automation_actions.email_action.send_plain_text_transactional")
    @patch("services.automation_actions.email_action.automation_safety_manager")
    def test_execute_send_email_sends_real_recipient(
        self, mock_safety, mock_txn, mock_gmail
    ):
        from services.automation_actions.email_action import EmailActionHandler

        handler = EmailActionHandler(MagicMock())
        mock_safety.check_rate_limits.return_value = {"allowed": True}
        mock_gmail.send_plain_text_as_user.return_value = {
            "success": True,
            "channel": "gmail",
            "message_id": "gm-2",
        }
        mock_txn.return_value = {"success": False}

        out = handler.execute_send_email(
            {"subject": "Hi", "body": "Body"},
            {"sender_email": "Lead <lead@gmail.com>", "_automation_rule_id": 4},
            11,
        )

        self.assertTrue(out.get("success"))
        self.assertNotIn("skipped", out.get("data", {}))
        mock_gmail.send_plain_text_as_user.assert_called_once()
        mock_txn.assert_not_called()


class TestMailboxAutoReplySkip(unittest.TestCase):
    def test_auto_reply_skips_gmail_send_for_example_com(self):
        from email_automation.actions import MinimalEmailActions

        mock_gmail = MagicMock()
        actions = MinimalEmailActions(services={"gmail": mock_gmail})
        actions.gmail_service = mock_gmail

        parsed = {
            "message_id": "m1",
            "thread_id": "t1",
            "headers": {"from": "Tester <a@example.com>", "subject": "Hello"},
            "snippet": "Hi",
        }

        with patch.object(
            actions, "_generate_reply_content", return_value=("Thanks", "template_fallback")
        ):
            result = actions._auto_reply(parsed, user_id=5)

        self.assertTrue(result.get("success"))
        self.assertFalse(result.get("details", {}).get("reply_sent"))
        self.assertTrue(result.get("details", {}).get("delivery_skipped"))
        mock_gmail.users().messages().send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
