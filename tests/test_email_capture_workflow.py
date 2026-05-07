"""Unit tests for services.email_capture_workflow (correlation_id + CRM upsert shim)."""

import unittest
from unittest.mock import MagicMock, patch


class EmailCaptureWorkflowTest(unittest.TestCase):
    @patch("services.email_capture_workflow.automation_engine")
    @patch("services.email_capture_workflow.enhanced_crm_service")
    def test_workflow_passes_correlation_and_lead_id_into_automation(self, mock_crm, mock_engine):
        from services.email_capture_workflow import run_inbound_email_workflow

        mock_crm.upsert_lead_from_inbound_email.return_value = {
            "success": True,
            "skipped": False,
            "data": {"lead_id": 42, "correlation_id": "fixed-corr"},
        }
        mock_engine.execute_automation_rules.return_value = {
            "success": True,
            "data": {"executed_rules": [], "failed_rules": []},
        }

        run_inbound_email_workflow(
            7,
            synced_email_row_id=100,
            external_message_id="msg-1",
            sender_header='"Pat" <pat@example.com>',
            subject="Hello",
            body_text="Body",
            provider="gmail",
            correlation_id="fixed-corr",
            mailbox_owner_email="owner@test.com",
        )

        mock_crm.upsert_lead_from_inbound_email.assert_called_once()
        args, kwargs = mock_crm.upsert_lead_from_inbound_email.call_args
        self.assertEqual(args[0], 7)
        self.assertEqual(kwargs.get("correlation_id"), "fixed-corr")

        mock_engine.execute_automation_rules.assert_called_once()
        trig_type, trig, uid = mock_engine.execute_automation_rules.call_args[0]
        self.assertEqual(trig["lead_id"], 42)
        self.assertEqual(trig["correlation_id"], "fixed-corr")
        self.assertEqual(trig["sender_email"], "pat@example.com")
        self.assertEqual(uid, 7)


if __name__ == "__main__":
    unittest.main()
