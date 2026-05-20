#!/usr/bin/env python3
"""Unified v2 email classification path tests."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from email_automation.email_classification import (
    SOURCE_LEGACY_WRAPPER,
    SOURCE_MAILBOX_SYNC,
    SOURCE_MANUAL_API,
    SOURCE_V2_FALLBACK,
    finalize_email_analysis,
    merge_legacy_compat_fields,
)


class TestUnifiedClassification(unittest.TestCase):
    def test_merge_legacy_compat_fields(self):
        raw = {
            "intent": "pricing_request",
            "confidence_score": 0.9,
            "recommended_action": "draft_reply",
            "urgency": "high",
        }
        out = merge_legacy_compat_fields(raw)
        self.assertEqual(out["intent"], "pricing_request")
        self.assertEqual(out["legacy_intent"], "lead_inquiry")
        self.assertEqual(out["confidence"], 0.9)
        self.assertIn("suggested_action", out)

    @patch("email_automation.ai_assistant.LLMRouter")
    @patch("core.redis_connection_helper.get_redis_client")
    def test_classify_email_intent_delegates_to_analyze(self, mock_redis, mock_router_class):
        mock_redis.return_value = None
        mock_router = MagicMock()
        mock_router.client.is_enabled.return_value = False
        mock_router_class.return_value = mock_router

        from email_automation.ai_assistant import MinimalAIEmailAssistant

        assistant = MinimalAIEmailAssistant(api_key=None)
        with patch.object(
            assistant,
            "analyze_incoming_email",
            wraps=assistant.analyze_incoming_email,
        ) as mock_analyze:
            result = assistant.classify_email_intent(
                "We need a quote for your services",
                "Pricing",
                user_id=1,
            )
            mock_analyze.assert_called_once()
            self.assertEqual(
                mock_analyze.call_args.kwargs.get("classification_source"),
                SOURCE_LEGACY_WRAPPER,
            )
        self.assertEqual(result["classification_source"], SOURCE_LEGACY_WRAPPER)
        self.assertIn("lead_score", result)
        self.assertIn("legacy_intent", result)

    @patch("email_automation.ai_assistant.LLMRouter")
    @patch("core.redis_connection_helper.get_redis_client")
    def test_manual_and_mailbox_share_v2_shape(self, mock_redis, mock_router_class):
        mock_redis.return_value = None
        mock_router = MagicMock()
        mock_router.client.is_enabled.return_value = False
        mock_router_class.return_value = mock_router

        from email_automation.ai_assistant import MinimalAIEmailAssistant

        assistant = MinimalAIEmailAssistant(api_key=None)

        manual = assistant.analyze_incoming_email(
            sender_email="a@example.com",
            sender_name="A",
            subject="Partnership",
            body="Let's explore a partnership collaboration.",
            classification_source=SOURCE_MANUAL_API,
        )
        mailbox = assistant.analyze_incoming_email(
            sender_email="b@example.com",
            sender_name="B",
            subject="Job",
            body="I am applying for a career role.",
            classification_source=SOURCE_MAILBOX_SYNC,
        )
        for payload in (manual, mailbox):
            self.assertIn("intent", payload)
            self.assertIn("secondary_intents", payload)
            self.assertIn("confidence_score", payload)
            self.assertIn("extracted_details", payload)
            self.assertIn("recommended_action_detail", payload)

        self.assertEqual(manual["classification_source"], SOURCE_MANUAL_API)
        self.assertEqual(mailbox["classification_source"], SOURCE_MAILBOX_SYNC)
        self.assertEqual(manual["intent"], "partnership_request")
        self.assertEqual(mailbox["intent"], "job_or_career_inquiry")

    @patch("email_automation.ai_assistant.LLMRouter")
    @patch("core.redis_connection_helper.get_redis_client")
    def test_invalid_llm_response_uses_fallback(self, mock_redis, mock_router_class):
        mock_redis.return_value = None
        mock_router = MagicMock()
        mock_router.client.is_enabled.return_value = True
        mock_router.process.return_value = {
            "success": False,
            "validated": False,
            "error": "schema fail",
        }
        mock_router_class.return_value = mock_router

        from email_automation.ai_assistant import MinimalAIEmailAssistant

        assistant = MinimalAIEmailAssistant(api_key=None)
        result = assistant.analyze_incoming_email(
            sender_email="x@example.com",
            sender_name="X",
            subject="Hello",
            body="General question",
        )
        self.assertEqual(result["classification_source"], SOURCE_V2_FALLBACK)
        self.assertTrue(result["needs_human_review"])

    @patch("email_automation.ai_assistant.LLMRouter")
    @patch("core.redis_connection_helper.get_redis_client")
    def test_generate_response_uses_analysis_context(self, mock_redis, mock_router_class):
        mock_redis.return_value = None
        mock_router = MagicMock()
        mock_router.client.is_enabled.return_value = True
        mock_router.process.return_value = {
            "success": True,
            "content": "Custom reply body",
        }
        mock_router_class.return_value = mock_router

        from email_automation.ai_assistant import MinimalAIEmailAssistant

        assistant = MinimalAIEmailAssistant(api_key=None)
        analysis = finalize_email_analysis(
            {
                "intent": "service_inquiry",
                "legacy_intent": "lead_inquiry",
                "confidence_score": 0.9,
                "suggested_reply": "Pre-drafted reply",
                "extracted_details": {
                    "requested_service": "automation",
                    "pain_points": ["slow inbox"],
                },
                "recommended_action_detail": {"next_best_action": "schedule_call"},
                "reply_guidance": {"tone": "professional_warm"},
            },
            classification_source=SOURCE_MANUAL_API,
        )
        reply = assistant.generate_response(
            "Need help",
            "Pat",
            "Services",
            analysis=analysis,
        )
        self.assertEqual(reply, "Pre-drafted reply")
        mock_router.process.assert_not_called()


if __name__ == "__main__":
    unittest.main()
