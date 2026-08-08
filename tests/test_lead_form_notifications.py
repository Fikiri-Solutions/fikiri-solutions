#!/usr/bin/env python3
"""Lead Slack notifier must fire without monitoring cooldown."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.lead_form_notifications import lead_slack_webhook_url, send_lead_slack_notification


class TestLeadFormNotifications(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "LEAD_SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/LEAD",
            "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/OPS",
        },
        clear=False,
    )
    def test_prefers_dedicated_lead_webhook(self):
        self.assertEqual(
            lead_slack_webhook_url(), "https://hooks.slack.com/services/LEAD"
        )

    @patch.dict(os.environ, {"LEAD_SLACK_WEBHOOK_URL": "", "SLACK_WEBHOOK_URL": ""}, clear=False)
    def test_returns_false_when_unconfigured(self):
        self.assertFalse(
            send_lead_slack_notification(title="Lead", text="hello", fields=[])
        )

    @patch.dict(
        os.environ,
        {
            "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/OPS",
            "LEAD_SLACK_WEBHOOK_URL": "",
            "SLACK_CHANNEL": "#leads",
        },
        clear=False,
    )
    @patch("requests.post")
    def test_posts_payload_without_raising(self, mock_post):
        mock_post.return_value = MagicMock(raise_for_status=MagicMock())
        ok = send_lead_slack_notification(
            title="New contact form: Jane",
            text="Need a demo",
            fields=[{"title": "Email", "value": "jane@example.com", "short": True}],
        )
        self.assertTrue(ok)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://hooks.slack.com/services/OPS")
        self.assertEqual(kwargs["json"]["channel"], "#leads")
        self.assertEqual(kwargs["json"]["attachments"][0]["title"], "New contact form: Jane")


if __name__ == "__main__":
    unittest.main()
