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


class TestAdvancedActionHandlerSignatures(unittest.TestCase):
    """Verify every action handler can be called through _execute_rule
    without a signature mismatch (the 3-arg call shape)."""

    def setUp(self):
        with patch("services.automation_engine.db_optimizer") as mock_db:
            with patch("services.automation_engine.enhanced_crm_service"):
                with patch("services.automation_engine.MinimalEmailParser"):
                    mock_db.execute_query.return_value = []
                    from services.automation_engine import (
                        AutomationEngine,
                        ActionType,
                    )
                    self.engine = AutomationEngine()
                    self.ActionType = ActionType

    def _call_handler(self, action_type, action_params, trigger_data=None):
        if trigger_data is None:
            trigger_data = {"lead_id": 99, "sender_email": "a@b.com", "subject": "hi"}
        handler = self.engine.action_handlers[action_type]
        return handler(action_params, trigger_data, 1)

    @patch("services.automation_engine.db_optimizer")
    def test_schedule_follow_up_signature(self, mock_db):
        mock_db.execute_query.return_value = None
        result = self._call_handler(
            self.ActionType.SCHEDULE_FOLLOW_UP,
            {"follow_up_type": "email", "follow_up_date": "2026-03-01"},
        )
        self.assertIsInstance(result, dict)

    @patch("services.automation_engine.db_optimizer")
    def test_create_calendar_event_signature(self, mock_db):
        mock_db.execute_query.return_value = None
        result = self._call_handler(
            self.ActionType.CREATE_CALENDAR_EVENT,
            {"title": "Demo", "date": "2026-03-01"},
        )
        self.assertIsInstance(result, dict)

    @patch("services.automation_engine.db_optimizer")
    @patch("services.automation_engine.enhanced_crm_service")
    def test_update_crm_field_direct(self, mock_crm, mock_db):
        mock_db.execute_query.return_value = None
        result = self._call_handler(
            self.ActionType.UPDATE_CRM_FIELD,
            {"field_name": "stage", "field_value": "qualified"},
            {"lead_id": 10},
        )
        self.assertIsInstance(result, dict)

    @patch("services.automation_engine.enhanced_crm_service")
    def test_update_crm_field_gmail_crm_preset(self, mock_crm):
        mock_crm.create_lead.return_value = {"success": True, "data": {"id": 42}}
        result = self._call_handler(
            self.ActionType.UPDATE_CRM_FIELD,
            {"slug": "gmail_crm", "target_stage": "new", "tags": ["inbox"]},
            {"sender_email": "lead@example.com", "subject": "Quote request"},
        )
        self.assertTrue(result["success"])
        mock_crm.create_lead.assert_called_once()

    @patch("services.automation_engine.enhanced_crm_service")
    def test_update_crm_field_lead_scoring_preset(self, mock_crm):
        mock_crm.update_lead.return_value = {"success": True}
        result = self._call_handler(
            self.ActionType.UPDATE_CRM_FIELD,
            {"slug": "lead_scoring", "min_score": 6},
            {"lead_id": 5, "score": 8},
        )
        self.assertTrue(result["success"])
        mock_crm.update_lead.assert_called_once_with(5, 1, {"score": 8})

    def test_trigger_webhook_signature(self):
        result = self._call_handler(
            self.ActionType.TRIGGER_WEBHOOK,
            {"webhook_url": "https://example.com/hook", "payload": {}},
        )
        self.assertTrue(result["success"])

    @patch("services.automation_engine.db_optimizer")
    def test_send_sms_signature(self, mock_db):
        mock_db.execute_query.return_value = None
        result = self._call_handler(
            self.ActionType.SEND_SMS,
            {"phone_number": "+1234567890", "message": "Hello"},
        )
        self.assertIsInstance(result, dict)

    @patch("services.automation_engine.db_optimizer")
    def test_create_invoice_signature(self, mock_db):
        mock_db.execute_query.return_value = None
        result = self._call_handler(
            self.ActionType.CREATE_INVOICE,
            {"amount": 100, "description": "Service fee"},
        )
        self.assertIsInstance(result, dict)

    @patch("services.automation_engine.db_optimizer")
    def test_assign_team_member_signature(self, mock_db):
        mock_db.execute_query.return_value = None
        result = self._call_handler(
            self.ActionType.ASSIGN_TEAM_MEMBER,
            {"team_member_id": 2, "assignment_type": "owner"},
        )
        self.assertIsInstance(result, dict)


class TestPresetRouteNoMatchReturnsError(unittest.TestCase):
    """The run-preset endpoint should return an error when no active rules match."""

    def setUp(self):
        with patch("services.automation_engine.db_optimizer") as mock_db:
            with patch("services.automation_engine.enhanced_crm_service"):
                with patch("services.automation_engine.MinimalEmailParser"):
                    mock_db.execute_query.return_value = []
                    from app import app
                    self.client = app.test_client()

    def test_preset_with_no_rules_returns_404(self):
        login_resp = self.client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "TestPass123!"
        })
        token = login_resp.get_json().get("data", {}).get("access_token")
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        resp = self.client.post(
            "/api/business/automation/test/preset",
            json={"preset_id": "gmail_crm", "user_id": 1},
            headers=headers,
        )
        data = resp.get_json()
        self.assertIn(resp.status_code, [404, 401])
        if resp.status_code == 404:
            self.assertFalse(data.get("success"))


if __name__ == "__main__":
    unittest.main()
