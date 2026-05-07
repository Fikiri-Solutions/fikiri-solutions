#!/usr/bin/env python3
"""
Email Pipeline Unit Tests
Tests for email_automation/pipeline.py
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


class TestEmailPipeline(unittest.TestCase):
    def test_parse_message_uses_parser(self):
        with patch("email_automation.pipeline.MinimalEmailParser") as mock_parser_cls:
            mock_parser = MagicMock()
            mock_parser.parse_message.return_value = {"message_id": "m1"}
            mock_parser_cls.return_value = mock_parser
            from email_automation import pipeline

            result = pipeline.parse_message({"id": "m1"})
            self.assertEqual(result["message_id"], "m1")
            mock_parser.parse_message.assert_called_once()

    def test_process_incoming_returns_parsed_when_no_actions(self):
        with patch("email_automation.pipeline.parse_message") as mock_parse:
            mock_parse.return_value = {"message_id": "m2"}
            from email_automation import pipeline

            result = pipeline.process_incoming({"id": "m2"}, actions=None)
            self.assertEqual(result["message_id"], "m2")
            mock_parse.assert_called_once()

    def test_process_incoming_orchestrates_flow(self):
        from email_automation import pipeline

        parsed = {
            "message_id": "m3",
            "headers": {"from": "a@b.com", "subject": "Need help"},
            "body": {"text": "hello", "html": ""},
            "snippet": "hello",
            "labels": []
        }

        actions = MagicMock()
        actions.services = {"ai_assistant": MagicMock()}
        actions.process_email.return_value = {"success": True, "action": "auto_reply"}

        wf_return = {
            "success": True,
            "correlation_id": "wf",
            "lead_capture": {"success": False, "data": {}},
            "automation": {"success": True},
        }

        with patch("email_automation.pipeline.parse_message", return_value=parsed), \
             patch("email_automation.pipeline.run_inbound_email_workflow", return_value=wf_return), \
             patch("email_automation.pipeline.MinimalEmailParser") as mock_parser_cls, \
             patch("email_automation.pipeline.automation_safety_manager") as mock_safety:
            mock_parser = MagicMock()
            mock_parser.get_subject.return_value = "Need help"
            mock_parser.get_body_text.return_value = "hello"
            mock_parser.get_sender.return_value = "a@b.com"
            mock_parser_cls.return_value = mock_parser
            mock_safety.check_rate_limits.return_value = {"allowed": True}

            actions.services["ai_assistant"]._load_business_context.return_value = {"company_name": "Fikiri"}
            actions.services["ai_assistant"].analyze_incoming_email.return_value = {
                "schema_version": "2026-05-email-analysis-v1",
                "intent": "lead_inquiry",
                "confidence": 0.91,
                "urgency": "medium",
                "business_value": "high",
                "recommended_action": "send_quote",
                "tone": "professional",
                "crm_updates": {
                    "stage": "qualified",
                    "tags": ["quote_request"],
                    "follow_up_needed": True,
                    "priority": "high",
                },
                "suggested_reply": "Thanks for reaching out.",
                "should_auto_send": True,
                "needs_human_review": False,
                "reason_for_recommendation": "Clear quote request.",
                "summary": "Lead asked for quote.",
            }

            result = pipeline.process_incoming({"id": "m3"}, actions=actions, user_id=1)

        self.assertTrue(result.get("success"))
        actions.services["ai_assistant"].analyze_incoming_email.assert_called_once()
        actions.process_email.assert_called_once_with(parsed, action_type="auto_reply", user_id=1)

    def test_process_incoming_draft_only_policy(self):
        from email_automation import pipeline

        parsed = {
            "message_id": "m4",
            "headers": {"from": "a@b.com", "subject": "Need help"},
            "body": {"text": "hello", "html": ""},
            "snippet": "hello",
            "labels": []
        }
        actions = MagicMock()
        actions.services = {"ai_assistant": MagicMock()}
        wf_return = {
            "success": True,
            "correlation_id": "wf",
            "lead_capture": {"success": False, "data": {}},
            "automation": {"success": True},
        }
        with patch("email_automation.pipeline.parse_message", return_value=parsed), \
             patch("email_automation.pipeline.run_inbound_email_workflow", return_value=wf_return), \
             patch("email_automation.pipeline.MinimalEmailParser") as mock_parser_cls, \
             patch("email_automation.pipeline.automation_safety_manager") as mock_safety:
            mock_parser = MagicMock()
            mock_parser.get_subject.return_value = "Need help"
            mock_parser.get_body_text.return_value = "hello"
            mock_parser.get_sender.return_value = "a@b.com"
            mock_parser_cls.return_value = mock_parser
            actions.services["ai_assistant"]._load_business_context.return_value = {"company_name": "Fikiri"}
            actions.services["ai_assistant"].analyze_incoming_email.return_value = {
                "schema_version": "2026-05-email-analysis-v1",
                "intent": "complaint",
                "confidence": 0.92,
                "urgency": "high",
                "business_value": "medium",
                "recommended_action": "escalate",
                "tone": "frustrated",
                "crm_updates": {
                    "stage": "replied",
                    "tags": ["complaint"],
                    "follow_up_needed": True,
                    "priority": "high",
                },
                "suggested_reply": "Thanks for flagging this issue.",
                "should_auto_send": True,
                "needs_human_review": False,
                "reason_for_recommendation": "Requires manager review.",
                "summary": "Customer complaint",
            }
            result = pipeline.process_incoming({"id": "m4"}, actions=actions, user_id=1)

        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("action", {}).get("action"), "draft_only")
        actions.process_email.assert_not_called()
        mock_safety.check_rate_limits.assert_not_called()


if __name__ == "__main__":
    unittest.main()
