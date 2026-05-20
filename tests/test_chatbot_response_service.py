#!/usr/bin/env python3
"""Unit tests for core.chatbot_response_service."""

import json
import os
import sys
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chatbot_config import ChatbotConfig
from core.chatbot_response_service import (
    ChatbotAnswerResult,
    build_chatbot_prompt,
    generate_chatbot_answer,
)


class TestChatbotResponseService(unittest.TestCase):
    def test_fallback_when_context_empty(self):
        result = generate_chatbot_answer(
            "What is X?",
            "",
            [],
            tenant_id="t1",
            user_id=1,
            fallback_needed=True,
            allow_llm=True,
        )
        self.assertIsInstance(result, ChatbotAnswerResult)
        self.assertTrue(result.fallback_used)
        self.assertIn("missing some context", result.answer)
        self.assertIsNone(result.llm_confidence)
        self.assertFalse(result.response_metadata.get("llm_attempted"))

    def test_prompt_includes_tone_and_business_name(self):
        cfg = ChatbotConfig(
            business_name="Acme Landscaping",
            chatbot_name="Green Helper",
            tone="warm and professional",
            restricted_topics=["pricing for competitors"],
        )
        prompt = build_chatbot_prompt("hours?", "Open 9-5 weekdays.", cfg)
        assert "Acme Landscaping" in prompt
        assert "Green Helper" in prompt
        assert "warm and professional" in prompt
        assert "pricing for competitors" in prompt

    @patch("core.chatbot_response_service.LLMRouter")
    def test_calls_llm_router_when_context_exists(self, mock_router_cls):
        mock_llm = Mock()
        mock_llm.process.return_value = {
            "success": True,
            "validated": True,
            "content": json.dumps({
                "answer": "We are open 9-5.",
                "confidence": 0.9,
                "fallback_used": False,
                "sources": ["doc_1"],
            }),
            "trace_id": "trace_abc",
        }
        mock_router_cls.return_value = mock_llm

        sources = [{
            "type": "knowledge_base",
            "id": "doc_1",
            "title": "Hours",
            "content": "Open 9-5",
            "relevance": 0.9,
        }]
        result = generate_chatbot_answer(
            "hours?",
            "KB: Open 9-5",
            sources,
            tenant_id="t1",
            user_id=5,
            conversation_id="conv_1",
            correlation_id="corr_1",
            billing_uid=5,
            fallback_needed=False,
            allow_llm=True,
        )

        mock_router_cls.assert_called_once()
        mock_llm.process.assert_called_once()
        call_kwargs = mock_llm.process.call_args[1]
        self.assertEqual(call_kwargs["intent"], "chatbot_response")
        self.assertEqual(result.answer, "We are open 9-5.")
        self.assertEqual(result.llm_trace_id, "trace_abc")
        self.assertTrue(result.response_metadata.get("llm_attempted"))
        self.assertGreaterEqual(result.confidence, 0.4)

    def test_fallback_uses_configured_message(self):
        cfg = ChatbotConfig(fallback_message="Custom fallback from Acme.")
        result = generate_chatbot_answer(
            "unknown?",
            "",
            [],
            tenant_id=None,
            user_id=None,
            fallback_needed=True,
            allow_llm=True,
            chatbot_config=cfg,
        )
        assert "Custom fallback from Acme" in result.answer

    @patch("core.chatbot_response_service.LLMRouter")
    def test_skips_llm_when_allow_llm_false(self, mock_router_cls):
        result = generate_chatbot_answer(
            "hours?",
            "some context",
            [{"type": "faq", "id": "1", "question": "q", "answer": "a", "confidence": 0.9}],
            tenant_id=None,
            user_id=None,
            fallback_needed=False,
            allow_llm=False,
        )
        mock_router_cls.assert_not_called()
        self.assertTrue(result.fallback_used)


if __name__ == "__main__":
    unittest.main()
