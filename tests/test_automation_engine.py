#!/usr/bin/env python3
"""
Automation Engine Unit Tests
Tests for services/automation_engine.py and core automation (trigger types, action types, safe paths)
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FLASK_ENV", "test")


class TestAutomationEngine(unittest.TestCase):
    def setUp(self):
        with patch("services.automation_engine.db_optimizer") as mock_db:
            with patch("services.automation_engine.enhanced_crm_service"):
                with patch("services.automation_engine.MinimalEmailParser"):
                    mock_db.execute_query.return_value = []
                    from services.automation_engine import (
                        AutomationEngine,
                        TriggerType,
                        ActionType,
                        AutomationStatus,
                    )

                    self.engine = AutomationEngine()
                    self.TriggerType = TriggerType
                    self.ActionType = ActionType
                    self.AutomationStatus = AutomationStatus

    def test_trigger_handlers_registered(self):
        self.assertIn(self.TriggerType.EMAIL_RECEIVED, self.engine.trigger_handlers)
        self.assertIn(self.TriggerType.LEAD_CREATED, self.engine.trigger_handlers)

    def test_action_handlers_registered(self):
        self.assertIn(self.ActionType.SEND_EMAIL, self.engine.action_handlers)
        self.assertIn(self.ActionType.UPDATE_LEAD_STAGE, self.engine.action_handlers)

    def test_trigger_type_values(self):
        self.assertEqual(self.TriggerType.EMAIL_RECEIVED.value, "email_received")
        self.assertEqual(self.TriggerType.LEAD_CREATED.value, "lead_created")

    def test_action_type_values(self):
        self.assertEqual(self.ActionType.SEND_EMAIL.value, "send_email")
        self.assertEqual(self.ActionType.UPDATE_LEAD_STAGE.value, "update_lead_stage")

    @patch("services.automation_engine.db_optimizer")
    def test_get_automation_rules_returns_dict(self, mock_db):
        mock_db.execute_query.side_effect = [[], [{"total": 0}]]
        result = self.engine.get_automation_rules(1)
        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("success"))
        self.assertIn("data", result)
        self.assertIn("rules", result["data"])
        self.assertIsInstance(result["data"]["rules"], list)

    def test_send_notification_without_webhook_returns_not_implemented(self):
        result = self.engine._execute_send_notification(
            {"message": "Hi", "type": "info"}, {}, 1
        )
        self.assertFalse(result.get("success"))
        self.assertEqual(result.get("error_code"), "NOT_IMPLEMENTED")

    @patch("requests.post")
    def test_send_notification_with_webhook_posts_to_slack(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.raise_for_status = MagicMock()
        result = self.engine._execute_send_notification(
            {"message": "Hi", "type": "info", "slack_webhook_url": "https://hooks.slack.com/x"},
            {},
            1,
        )
        self.assertTrue(result.get("success"))
        mock_post.assert_called_once()
        call_kw = mock_post.call_args[1]
        self.assertIn("text", call_kw["json"])
        self.assertIn("info", call_kw["json"]["text"])


if __name__ == "__main__":
    unittest.main()
