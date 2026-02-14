#!/usr/bin/env python3
"""
Email Action Handlers Unit Tests
Tests for services/email_action_handlers.py
"""

import unittest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")

from services.email_action_handlers import EmailActionHandler


class _Token:
    def __init__(self, access_token="token", expires_at=None):
        self.access_token = access_token
        self.expires_at = expires_at


class TestEmailActionHandlers(unittest.TestCase):
    def setUp(self):
        self.handler = EmailActionHandler()
        self.handler.oauth_manager = MagicMock()

    @patch("services.email_action_handlers.requests.post")
    def test_archive_email_success(self, mock_post):
        self.handler.oauth_manager.get_user_tokens.return_value = _Token()
        mock_post.return_value.status_code = 200

        with patch.object(self.handler, "_log_email_action") as log_action:
            result = self.handler.archive_email(user_id=1, email_id="m1")

        self.assertTrue(result.get("success"))
        log_action.assert_called_once()

    def test_archive_email_refresh_failure(self):
        expired = _Token(expires_at=datetime.now() - timedelta(days=1))
        self.handler.oauth_manager.get_user_tokens.side_effect = [expired]
        self.handler.oauth_manager.refresh_access_token.return_value = {"success": False}

        result = self.handler.archive_email(user_id=1, email_id="m1")
        self.assertFalse(result.get("success"))
        self.assertIn("refresh token", result.get("error", "").lower())

    def test_tag_email_no_valid_labels(self):
        self.handler.oauth_manager.get_user_tokens.return_value = _Token()

        with patch.object(self.handler, "_get_or_create_label", return_value=None):
            result = self.handler.tag_email(user_id=1, email_id="m1", tags=["VIP", "Lead"])

        self.assertFalse(result.get("success"))
        self.assertIn("No valid labels", result.get("error", ""))

    @patch("services.email_action_handlers.requests.post")
    @patch("services.email_action_handlers.requests.get")
    def test_forward_email_success(self, mock_get, mock_post):
        self.handler.oauth_manager.get_user_tokens.return_value = _Token()
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Hello"},
                    {"name": "From", "value": "Jane <jane@example.com>"},
                ]
            }
        }
        mock_post.return_value.status_code = 200

        with patch.object(self.handler, "_create_message_raw", return_value="raw") as create_raw:
            with patch.object(self.handler, "_log_email_action") as log_action:
                result = self.handler.forward_email(
                    user_id=1, email_id="m1", to_email="to@example.com", message="Hi"
                )

        self.assertTrue(result.get("success"))
        create_raw.assert_called_once()
        log_action.assert_called_once()

    @patch("services.email_action_handlers.requests.post")
    @patch("services.email_action_handlers.requests.get")
    def test_send_ai_response_cleans_email(self, mock_get, mock_post):
        self.handler.oauth_manager.get_user_tokens.return_value = _Token()
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "payload": {
                "headers": [
                    {"name": "From", "value": "John Doe <john@example.com>"},
                    {"name": "Subject", "value": "Question"},
                ]
            }
        }
        mock_post.return_value.status_code = 200

        with patch.object(self.handler, "_create_message_raw", return_value="raw") as create_raw:
            with patch.object(self.handler, "_log_email_action") as log_action:
                result = self.handler.send_ai_response(user_id=1, email_id="m1", ai_response="Thanks")

        self.assertTrue(result.get("success"))
        # Ensure cleaned email address passed to raw creator
        args, _ = create_raw.call_args
        self.assertEqual(args[0], "john@example.com")
        log_action.assert_called_once()


if __name__ == "__main__":
    unittest.main()
