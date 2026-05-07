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

from services.automation_engine import (  # noqa: E402
    AutomationEngine,
    AutomationStatus,
    ActionType,
    TriggerType,
    INBOUND_CRM_SYNC_SLUG,
    _is_inbound_crm_sync_slug,
)


class TestAutomationEngine(unittest.TestCase):
    def setUp(self):
        with patch("services.automation_engine.db_optimizer") as mock_db:
            with patch("services.automation_engine.MinimalEmailParser"):
                mock_db.execute_query.return_value = []
                self.engine = AutomationEngine()
                self.TriggerType = TriggerType
                self.ActionType = ActionType
                self.AutomationStatus = AutomationStatus

    def test_trigger_handlers_registered(self):
        self.assertIn(self.TriggerType.EMAIL_RECEIVED, self.engine.trigger_handlers)
        self.assertIn(self.TriggerType.LEAD_CREATED, self.engine.trigger_handlers)

    def test_action_handlers_registered(self):
        self.assertIn(self.ActionType.SEND_EMAIL, self.engine.action_handlers)
        self.assertIn(self.ActionType.SEND_SMS, self.engine.action_handlers)
        self.assertIn(self.ActionType.TRIGGER_WEBHOOK, self.engine.action_handlers)
        self.assertIn(self.ActionType.UPDATE_CRM_FIELD, self.engine.action_handlers)
        self.assertIn(self.ActionType.UPDATE_LEAD_STAGE, self.engine.action_handlers)
        self.assertIn(self.ActionType.ADD_LEAD_ACTIVITY, self.engine.action_handlers)
        send_handler = self.engine.action_handlers[self.ActionType.SEND_EMAIL]
        sms_handler = self.engine.action_handlers[self.ActionType.SEND_SMS]
        webhook_handler = self.engine.action_handlers[self.ActionType.TRIGGER_WEBHOOK]
        crm_field_handler = self.engine.action_handlers[self.ActionType.UPDATE_CRM_FIELD]
        crm_stage_handler = self.engine.action_handlers[self.ActionType.UPDATE_LEAD_STAGE]
        crm_activity_handler = self.engine.action_handlers[self.ActionType.ADD_LEAD_ACTIVITY]
        self.assertIs(send_handler.__self__, self.engine.email_action_handler)
        self.assertEqual(send_handler.__func__.__name__, "execute_send_email")
        self.assertIs(sms_handler.__self__, self.engine.sms_action_handler)
        self.assertEqual(sms_handler.__func__.__name__, "execute_send_sms")
        self.assertIs(webhook_handler.__self__, self.engine.webhook_action_handler)
        self.assertEqual(webhook_handler.__func__.__name__, "execute_trigger_webhook")
        self.assertIs(crm_field_handler.__self__, self.engine.crm_action_handler)
        self.assertEqual(crm_field_handler.__func__.__name__, "execute_update_crm_field")
        self.assertIs(crm_stage_handler.__self__, self.engine.crm_action_handler)
        self.assertEqual(crm_stage_handler.__func__.__name__, "execute_update_lead_stage")
        self.assertIs(crm_activity_handler.__self__, self.engine.crm_action_handler)
        self.assertEqual(crm_activity_handler.__func__.__name__, "execute_add_lead_activity")

    def test_execute_send_sms_wrapper_delegates_to_handler(self):
        expected = {"success": True, "error": None}
        self.engine.sms_action_handler.execute_send_sms = MagicMock(return_value=expected)
        out = self.engine._execute_send_sms({"message": "Hi"}, {"lead_id": 1}, 5)
        self.assertEqual(out, expected)
        self.engine.sms_action_handler.execute_send_sms.assert_called_once_with(
            action_data={"message": "Hi"},
            trigger_data={"lead_id": 1},
            user_id=5,
        )

    def test_execute_update_crm_field_wrapper_delegates_to_handler(self):
        expected = {"success": True, "data": {"lead_id": 9}}
        self.engine.crm_action_handler.execute_update_crm_field = MagicMock(return_value=expected)
        out = self.engine._execute_update_crm_field({"field_name": "stage"}, {"lead_id": 9}, 1)
        self.assertEqual(out, expected)
        self.engine.crm_action_handler.execute_update_crm_field.assert_called_once_with(
            action_data={"field_name": "stage"},
            trigger_data={"lead_id": 9},
            user_id=1,
        )

    def test_execute_trigger_webhook_wrapper_delegates_to_handler(self):
        expected = {"success": True, "data": {"status_code": 200}}
        self.engine.webhook_action_handler.execute_trigger_webhook = MagicMock(
            return_value=expected
        )
        out = self.engine._execute_trigger_webhook({"webhook_url": "https://example.com"}, {}, 1)
        self.assertEqual(out, expected)
        self.engine.webhook_action_handler.execute_trigger_webhook.assert_called_once_with(
            parameters={"webhook_url": "https://example.com"},
            trigger_data={},
            user_id=1,
        )

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
        # Ensure no global Slack URL leaks success when env has SLACK_WEBHOOK_URL set (CI/local).
        with patch.dict(os.environ, {"SLACK_WEBHOOK_URL": ""}, clear=False):
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

    def test_send_email_missing_recipient(self):
        result = self.engine._execute_send_email({}, {}, 1)
        self.assertFalse(result.get("success"))
        self.assertEqual(result.get("error_code"), "MISSING_RECIPIENT")

    @patch("services.automation_actions.email_action.automation_safety_manager")
    @patch("services.automation_actions.email_action.send_plain_text_transactional")
    @patch("services.automation_actions.email_action.gmail_client")
    def test_send_email_succeeds_via_gmail_client(
        self, mock_gc_singleton, mock_txn, mock_safety
    ):
        mock_safety.check_rate_limits.return_value = {"allowed": True}
        mock_gc_singleton.send_plain_text_as_user.return_value = {
            "success": True,
            "channel": "gmail",
            "message_id": "m1",
        }
        mock_txn.return_value = {"success": False}

        result = self.engine._execute_send_email(
            {"subject": "Hi", "body": "Hello"},
            {"sender_email": "Lead <lead@example.com>", "_automation_rule_id": 9},
            42,
        )
        self.assertTrue(result.get("success"))
        self.assertEqual(result["data"]["recipient"], "lead@example.com")
        mock_gc_singleton.send_plain_text_as_user.assert_called_once()
        mock_txn.assert_not_called()

    @patch("services.automation_actions.email_action.automation_safety_manager")
    @patch("services.automation_actions.email_action.workflow_schedule_follow_up")
    @patch("services.automation_actions.email_action.db_optimizer")
    def test_delayed_send_rejects_recipient_vs_lead_mismatch(
        self, mock_db, mock_schedule, mock_safety
    ):
        mock_safety.check_rate_limits.return_value = {"allowed": True}
        mock_db.execute_query.return_value = [{"email": "other@example.com"}]
        mock_schedule.side_effect = AssertionError(
            "schedule_follow_up must not run when lead email mismatches recipient"
        )
        result = self.engine._execute_send_email(
            {"delay_minutes": 60, "body": "later"},
            {"lead_id": 3, "sender_email": "self@example.com"},
            77,
        )
        self.assertFalse(result.get("success"))
        self.assertEqual(result.get("error_code"), "DELAYED_SEND_RECIPIENT_MISMATCH")
        mock_schedule.assert_not_called()

    def test_parse_email_rejects_bulk_recipients(self):
        self.assertEqual(self.engine._parse_email_address("a@b.com, c@d.com"), "")

    def test_parse_email_strips_crlf_padding(self):
        self.assertEqual(self.engine._parse_email_address("who@example.com\r\n"), "who@example.com")

    def test_sanitize_subject_strips_newlines(self):
        self.assertEqual(
            self.engine._sanitize_email_subject("Hello\r\nForged: bogus"),
            "HelloForged: bogus",
        )

    def test_merge_lead_id_into_trigger_from_crm_style_result(self):
        td = {"sender_email": "a@b.com"}
        self.engine._merge_lead_id_into_trigger(
            td,
            {"success": True, "data": {"lead_id": 15, "action": "lead_created"}},
        )
        self.assertEqual(td["lead_id"], 15)

    def test_merge_lead_id_from_nested_lead_object(self):
        td = {}
        self.engine._merge_lead_id_into_trigger(
            td,
            {"success": True, "data": {"lead": {"id": "22"}}},
        )
        self.assertEqual(td["lead_id"], 22)

    def test_inbound_crm_sync_slug_accepts_legacy_gmail_crm(self):
        self.assertTrue(_is_inbound_crm_sync_slug(INBOUND_CRM_SYNC_SLUG))
        self.assertTrue(_is_inbound_crm_sync_slug("gmail_crm"))
        self.assertFalse(_is_inbound_crm_sync_slug("lead_scoring"))
        self.assertFalse(_is_inbound_crm_sync_slug(None))

    @patch("services.automation_actions.crm_action.enhanced_crm_service.update_lead")
    @patch("services.automation_actions.crm_action.db_optimizer")
    def test_update_crm_field_inbound_slug_merge_is_alias_safe(
        self, mock_db, mock_update
    ):
        mock_db.execute_query.return_value = [{"id": 5}]
        mock_update.return_value = {"success": True}
        for slug in (INBOUND_CRM_SYNC_SLUG, "gmail_crm"):
            with self.subTest(slug=slug):
                mock_update.reset_mock()
                out = self.engine._execute_update_crm_field(
                    {"slug": slug, "target_stage": "qualified", "tags": ["inbox"]},
                    {"lead_id": 5, "correlation_id": "c99"},
                    1,
                )
                self.assertTrue(out.get("success"), msg=out)
                mock_update.assert_called_once()


if __name__ == "__main__":
    unittest.main()
