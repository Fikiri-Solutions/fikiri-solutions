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


if __name__ == "__main__":
    unittest.main()
