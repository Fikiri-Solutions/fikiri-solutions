#!/usr/bin/env python3
"""Tests for core.chatbot_lead_capture."""

import os
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chatbot_config import ChatbotConfig
from core.chatbot_lead_capture import capture_chatbot_lead, extract_lead_info


class TestExtractLeadInfo(unittest.TestCase):
    def test_extracts_from_explicit_payload(self):
        info = extract_lead_info(
            "hello",
            {"email": "lead@example.com", "phone": "555-123-4567", "name": "Alex"},
        )
        self.assertEqual(info["email"], "lead@example.com")
        self.assertEqual(info["phone"], "555-123-4567")
        self.assertEqual(info["name"], "Alex")

    def test_extracts_email_from_query_text(self):
        info = extract_lead_info("Contact me at visitor@example.com please", {})
        self.assertEqual(info["email"], "visitor@example.com")
        self.assertEqual(info["name"], "Visitor")


class TestCaptureChatbotLead(unittest.TestCase):
    @patch("core.chatbot_lead_capture.enhanced_crm_service.add_lead_activity")
    @patch("core.chatbot_lead_capture.enhanced_crm_service.create_lead")
    @patch("core.chatbot_lead_capture.db_optimizer.execute_query")
    def test_creates_lead_from_explicit_payload(
        self, mock_execute, mock_create_lead, mock_add_activity
    ):
        mock_execute.return_value = []
        mock_create_lead.return_value = {"success": True, "data": {"lead_id": 42}}

        lead_id = capture_chatbot_lead(
            user_id=7,
            query="hello",
            lead_payload={"email": "lead@example.com", "name": "Pat"},
            conversation_id="conv-1",
            tenant_id="tenant-7",
        )

        self.assertEqual(lead_id, 42)
        mock_create_lead.assert_called_once_with(
            7,
            {
                "email": "lead@example.com",
                "name": "Pat",
                "phone": None,
                "source": "chatbot_widget",
                "metadata": {"conversation_id": "conv-1", "tenant_id": "tenant-7"},
            },
        )
        mock_add_activity.assert_called_once()

    @patch("core.chatbot_lead_capture.enhanced_crm_service.add_lead_activity")
    @patch("core.chatbot_lead_capture.enhanced_crm_service.create_lead")
    @patch("core.chatbot_lead_capture.db_optimizer.execute_query")
    def test_creates_lead_from_query_text(
        self, mock_execute, mock_create_lead, mock_add_activity
    ):
        mock_execute.return_value = []
        mock_create_lead.return_value = {"success": True, "data": {"lead_id": 99}}

        lead_id = capture_chatbot_lead(
            user_id=7,
            query="Email me at query@example.com",
            lead_payload={},
            conversation_id="conv-2",
            tenant_id="tenant-7",
        )

        self.assertEqual(lead_id, 99)
        mock_create_lead.assert_called_once()
        mock_add_activity.assert_called_once()

    @patch("core.chatbot_lead_capture.enhanced_crm_service.add_lead_activity")
    @patch("core.chatbot_lead_capture.enhanced_crm_service.create_lead")
    @patch("core.chatbot_lead_capture.db_optimizer.execute_query")
    def test_duplicate_email_reuses_existing_lead(
        self, mock_execute, mock_create_lead, mock_add_activity
    ):
        mock_execute.return_value = [{"id": 555}]

        lead_id = capture_chatbot_lead(
            user_id=7,
            query="Still interested",
            lead_payload={"email": "existing@example.com"},
            conversation_id="conv-3",
            tenant_id="tenant-7",
        )

        self.assertEqual(lead_id, 555)
        mock_create_lead.assert_not_called()
        mock_add_activity.assert_called_once_with(
            555,
            7,
            "note_added",
            "Chatbot conversation captured lead info",
            metadata={"conversation_id": "conv-3", "query": "Still interested"},
        )

    @patch("core.chatbot_lead_capture.logger.info")
    @patch("core.chatbot_lead_capture.enhanced_crm_service.create_lead")
    def test_lead_capture_disabled_skips_creation(self, mock_create_lead, mock_log_info):
        lead_id = capture_chatbot_lead(
            user_id=7,
            query="Email me at skip@example.com",
            lead_payload={},
            conversation_id="conv-4",
            tenant_id="tenant-7",
            chatbot_config=ChatbotConfig(lead_capture_enabled=False),
        )

        self.assertIsNone(lead_id)
        mock_create_lead.assert_not_called()
        mock_log_info.assert_called_once()
        extra = mock_log_info.call_args[1]["extra"]
        self.assertEqual(extra["event"], "chatbot.lead_capture.skipped")
        self.assertEqual(extra["reason"], "disabled_by_config")

    @patch("core.chatbot_lead_capture.logger.info")
    @patch("core.chatbot_lead_capture.enhanced_crm_service.add_lead_activity")
    @patch("core.chatbot_lead_capture.enhanced_crm_service.create_lead")
    @patch("core.chatbot_lead_capture.db_optimizer.execute_query")
    def test_completed_created_lead_logs_created_true(
        self, mock_execute, mock_create_lead, mock_add_activity, mock_log_info
    ):
        mock_execute.return_value = []
        mock_create_lead.return_value = {"success": True, "data": {"lead_id": 42}}

        lead_id = capture_chatbot_lead(
            user_id=7,
            query="hello",
            lead_payload={"email": "lead@example.com", "name": "Pat"},
            conversation_id="conv-log-1",
            tenant_id="tenant-7",
        )

        self.assertEqual(lead_id, 42)
        completed_calls = [
            call
            for call in mock_log_info.call_args_list
            if call[1].get("extra", {}).get("event") == "chatbot.lead_capture.completed"
        ]
        self.assertEqual(len(completed_calls), 1)
        extra = completed_calls[0][1]["extra"]
        self.assertTrue(extra["created"])
        self.assertEqual(extra["lead_id"], 42)
        self.assertTrue(extra["has_email"])
        self.assertTrue(extra["conversation_id_present"])

    @patch("core.chatbot_lead_capture.logger.info")
    @patch("core.chatbot_lead_capture.enhanced_crm_service.add_lead_activity")
    @patch("core.chatbot_lead_capture.enhanced_crm_service.create_lead")
    @patch("core.chatbot_lead_capture.db_optimizer.execute_query")
    def test_completed_existing_lead_logs_created_false(
        self, mock_execute, mock_create_lead, mock_add_activity, mock_log_info
    ):
        mock_execute.return_value = [{"id": 555}]

        lead_id = capture_chatbot_lead(
            user_id=7,
            query="Still interested",
            lead_payload={"email": "existing@example.com"},
            conversation_id="conv-log-2",
            tenant_id="tenant-7",
        )

        self.assertEqual(lead_id, 555)
        completed_calls = [
            call
            for call in mock_log_info.call_args_list
            if call[1].get("extra", {}).get("event") == "chatbot.lead_capture.completed"
        ]
        self.assertEqual(len(completed_calls), 1)
        extra = completed_calls[0][1]["extra"]
        self.assertFalse(extra["created"])
        self.assertEqual(extra["lead_id"], 555)

    @patch("core.chatbot_lead_capture.logger.warning")
    @patch("core.chatbot_lead_capture.enhanced_crm_service.add_lead_activity")
    @patch("core.chatbot_lead_capture.enhanced_crm_service.create_lead")
    @patch("core.chatbot_lead_capture.db_optimizer.execute_query")
    def test_crm_failure_logs_failed(self, mock_execute, mock_create_lead, mock_add_activity, mock_log_warning):
        mock_execute.side_effect = RuntimeError("db down")

        lead_id = capture_chatbot_lead(
            user_id=7,
            query="Email me at fail@example.com",
            lead_payload={},
            conversation_id="conv-5",
            tenant_id="tenant-7",
        )

        self.assertIsNone(lead_id)
        mock_create_lead.assert_not_called()
        mock_add_activity.assert_not_called()
        mock_log_warning.assert_called_once()
        extra = mock_log_warning.call_args[1]["extra"]
        self.assertEqual(extra["event"], "chatbot.lead_capture.failed")
        self.assertEqual(extra["error_type"], "RuntimeError")

    @patch("core.chatbot_lead_capture.logger.info")
    @patch("core.chatbot_lead_capture.enhanced_crm_service.create_lead")
    @patch("core.chatbot_lead_capture.db_optimizer.execute_query")
    def test_logs_do_not_include_sensitive_values(self, mock_execute, mock_create_lead, mock_log_info):
        mock_execute.return_value = []
        mock_create_lead.return_value = {"success": True, "data": {"lead_id": 88}}

        capture_chatbot_lead(
            user_id=7,
            query="SECRET_QUERY with secret@example.com and 555-123-4567",
            lead_payload={"email": "secret@example.com", "phone": "555-123-4567"},
            conversation_id="conv-sensitive",
            tenant_id="tenant-7",
        )

        log_blob = str(mock_log_info.call_args_list)
        self.assertNotIn("secret@example.com", log_blob)
        self.assertNotIn("555-123-4567", log_blob)
        self.assertNotIn("SECRET_QUERY", log_blob)

    @patch("core.chatbot_lead_capture.logger.info")
    @patch("core.chatbot_lead_capture.enhanced_crm_service.create_lead")
    def test_collect_email_false_logs_collect_email_disabled(self, mock_create_lead, mock_log_info):
        lead_id = capture_chatbot_lead(
            user_id=7,
            query="Email me at hidden@example.com",
            lead_payload={},
            conversation_id="conv-6",
            tenant_id="tenant-7",
            chatbot_config=ChatbotConfig(collect_email=False, collect_phone=False),
        )

        self.assertIsNone(lead_id)
        mock_create_lead.assert_not_called()
        skipped_calls = [
            call
            for call in mock_log_info.call_args_list
            if call[1].get("extra", {}).get("event") == "chatbot.lead_capture.skipped"
        ]
        self.assertEqual(len(skipped_calls), 1)
        self.assertEqual(skipped_calls[0][1]["extra"]["reason"], "collect_email_disabled")


if __name__ == "__main__":
    unittest.main()
