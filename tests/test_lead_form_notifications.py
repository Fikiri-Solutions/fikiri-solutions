#!/usr/bin/env python3
"""Lead Slack notifier must fire without monitoring cooldown."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.lead_form_notifications import (
    lead_dedupe_key,
    lead_slack_webhook_url,
    reset_lead_slack_dedupe_cache,
    send_lead_slack_notification,
    uses_dedicated_lead_webhook,
)


class TestLeadFormNotifications(unittest.TestCase):
    def setUp(self):
        reset_lead_slack_dedupe_cache()

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
        self.assertTrue(uses_dedicated_lead_webhook())

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
    def test_fallback_webhook_may_set_channel(self, mock_post):
        mock_post.return_value = MagicMock(raise_for_status=MagicMock())
        ok = send_lead_slack_notification(
            title="New contact form: Jane",
            text="Need a demo",
            fields=[{"title": "Email", "value": "jane@example.com", "short": True}],
            blocking=True,
        )
        self.assertTrue(ok)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://hooks.slack.com/services/OPS")
        self.assertEqual(kwargs["json"]["channel"], "#leads")
        self.assertEqual(kwargs["json"]["attachments"][0]["title"], "New contact form: Jane")

    @patch.dict(
        os.environ,
        {
            "LEAD_SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/LEAD",
            "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/OPS",
            "LEAD_SLACK_CHANNEL": "#ignored",
        },
        clear=False,
    )
    @patch("requests.post")
    def test_dedicated_webhook_skips_channel_override(self, mock_post):
        mock_post.return_value = MagicMock(raise_for_status=MagicMock())
        ok = send_lead_slack_notification(
            title="Lead",
            text="hi",
            blocking=True,
        )
        self.assertTrue(ok)
        payload = mock_post.call_args.kwargs["json"]
        self.assertNotIn("channel", payload)
        self.assertEqual(mock_post.call_args.args[0], "https://hooks.slack.com/services/LEAD")

    @patch.dict(
        os.environ,
        {
            "LEAD_SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/LEAD",
            "FIKIRI_LEAD_SLACK_DEDUPE_SECONDS": "900",
        },
        clear=False,
    )
    @patch("requests.post")
    def test_dedupe_suppresses_retry(self, mock_post):
        mock_post.return_value = MagicMock(raise_for_status=MagicMock())
        key = lead_dedupe_key("contact", "jane@example.com", "same")
        self.assertTrue(
            send_lead_slack_notification(
                title="One", text="a", dedupe_key=key, blocking=True
            )
        )
        self.assertFalse(
            send_lead_slack_notification(
                title="Two", text="b", dedupe_key=key, blocking=True
            )
        )
        self.assertEqual(mock_post.call_count, 1)

    @patch.dict(
        os.environ,
        {"LEAD_SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/LEAD"},
        clear=False,
    )
    @patch("requests.post")
    def test_slack_http_failure_returns_false(self, mock_post):
        mock_post.side_effect = RuntimeError("boom")
        self.assertFalse(
            send_lead_slack_notification(title="Lead", text="x", blocking=True)
        )


if __name__ == "__main__":
    unittest.main()
