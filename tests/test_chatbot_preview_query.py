#!/usr/bin/env python3
"""Tests for POST /api/chatbot/preview-query (dashboard builder preview)."""

import json
import os
import sys
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("SKIP_HEAVY_DEP_CHECKS", "true")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from core.chatbot_smart_faq_api import chatbot_bp
from core.chatbot_config import ChatbotConfig
from core.chatbot_retrieval import RetrievalResult
from core.chatbot_response_service import ChatbotAnswerResult


class TestChatbotPreviewQuery(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(chatbot_bp)
        self.client = self.app.test_client()

    def test_preview_requires_auth(self):
        with patch("core.chatbot_smart_faq_api.get_current_user_id", return_value=None):
            resp = self.client.post(
                "/api/chatbot/preview-query",
                json={"query": "hello"},
            )
        self.assertEqual(resp.status_code, 401)

    @patch("core.chatbot_smart_faq_api.generate_chatbot_answer")
    @patch("core.chatbot_smart_faq_api.load_chatbot_config")
    @patch("core.chatbot_smart_faq_api.retrieve_chatbot_context")
    @patch("core.chatbot_smart_faq_api.get_current_user_id")
    def test_preview_uses_retrieval_and_response_facades(
        self, mock_uid, mock_retrieve, mock_load_cfg, mock_generate
    ):
        mock_uid.return_value = 42
        mock_retrieve.return_value = RetrievalResult(
            sources=[{"type": "faq", "id": "f1", "question": "Q", "answer": "A", "confidence": 0.9}],
            snippets=[],
            context_text="FAQ: A",
            retrieval_confidence=0.9,
            fallback_needed=False,
            source_count=1,
        )
        mock_load_cfg.return_value = ChatbotConfig(business_name="Acme", tone="warm")
        mock_generate.return_value = ChatbotAnswerResult(
            answer="We are open 9-5.",
            confidence=0.85,
            llm_confidence=0.8,
            combined_confidence=0.85,
            fallback_used=False,
            escalation_recommended=False,
            llm_trace_id="trace_p",
            retrieval_confidence=0.9,
        )

        resp = self.client.post(
            "/api/chatbot/preview-query",
            json={"query": "What are your hours?"},
        )

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["answer"], "We are open 9-5.")
        self.assertTrue(data["config_applied"])
        self.assertFalse(data["fallback_used"])

        mock_retrieve.assert_called_once()
        retrieve_args = mock_retrieve.call_args
        self.assertEqual(retrieve_args[0], ("What are your hours?", "42", 42))
        self.assertIn("correlation_id", retrieve_args[1])
        mock_load_cfg.assert_called_once_with(42, tenant_id="42")
        mock_generate.assert_called_once()
        gen_kwargs = mock_generate.call_args[1]
        self.assertEqual(gen_kwargs["billing_uid"], 42)
        self.assertTrue(gen_kwargs["allow_llm"])
        self.assertEqual(gen_kwargs["chatbot_config"].business_name, "Acme")

    @patch("core.chatbot_smart_faq_api.generate_chatbot_answer")
    @patch("core.chatbot_smart_faq_api.load_chatbot_config")
    @patch("core.chatbot_smart_faq_api.retrieve_chatbot_context")
    @patch("core.chatbot_smart_faq_api.get_current_user_id")
    def test_preview_does_not_create_lead_or_track_api_usage(
        self, mock_uid, mock_retrieve, mock_load_cfg, mock_generate
    ):
        mock_uid.return_value = 5
        mock_retrieve.return_value = RetrievalResult(
            sources=[],
            snippets=[],
            context_text="",
            retrieval_confidence=0.0,
            fallback_needed=True,
            source_count=0,
        )
        mock_load_cfg.return_value = ChatbotConfig()
        mock_generate.return_value = ChatbotAnswerResult(
            answer="fallback",
            confidence=0.2,
            llm_confidence=None,
            combined_confidence=0.2,
            fallback_used=True,
            escalation_recommended=True,
            llm_trace_id=None,
            retrieval_confidence=0.0,
        )

        with patch("crm.service.enhanced_crm_service.create_lead") as mock_lead:
            with patch("core.public_chatbot_api.api_key_manager.record_usage") as mock_usage:
                resp = self.client.post(
                    "/api/chatbot/preview-query",
                    json={"query": "contact me at test@example.com"},
                )

        self.assertEqual(resp.status_code, 200)
        mock_lead.assert_not_called()
        mock_usage.assert_not_called()

    @patch("core.public_chatbot_api.load_chatbot_config")
    @patch("core.chatbot_response_service.LLMRouter")
    @patch("core.chatbot_retrieval.get_feature_flags")
    @patch("core.chatbot_retrieval.faq_system.search_faqs")
    @patch("core.chatbot_retrieval.knowledge_base.search")
    @patch("core.public_chatbot_api.api_key_manager.validate_api_key")
    @patch("core.public_chatbot_api.api_key_manager.check_rate_limit")
    @patch("core.public_chatbot_api.api_key_manager.record_usage")
    @patch("core.chatbot_usage_tracking.check_plan_access")
    @patch("core.public_chatbot_api.context_system.start_conversation")
    def test_public_query_unchanged_alongside_preview(
        self,
        mock_start_conv,
        mock_plan,
        mock_record,
        mock_rate,
        mock_validate,
        mock_kb,
        mock_faq,
        mock_flags,
        mock_llm_router,
        mock_public_load,
    ):
        from core.public_chatbot_api import public_chatbot_bp

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(public_chatbot_bp)
        public_client = app.test_client()

        mock_validate.return_value = {
            "api_key_id": 1,
            "user_id": 5,
            "tenant_id": "t5",
            "scopes": ["chatbot:query"],
        }
        mock_rate.return_value = {"allowed": True, "remaining": 10, "limit": 60}
        mock_plan.return_value = {"plan": "starter", "allow_llm": True}
        mock_flags.return_value.is_enabled.return_value = False
        mock_faq.return_value = Mock(success=True, matches=[])
        mock_doc = Mock(id="d1", title="T", content="Production context.")
        mock_kb.return_value = Mock(
            success=True,
            results=[Mock(document=mock_doc, relevance_score=0.9)],
        )
        mock_start_conv.return_value = Mock(conversation_id="c1")
        mock_public_load.return_value = ChatbotConfig()
        mock_llm = Mock()
        mock_llm.process.return_value = {
            "success": True,
            "validated": True,
            "content": json.dumps({
                "answer": "public answer",
                "confidence": 0.9,
                "fallback_used": False,
                "sources": [],
            }),
            "trace_id": "t1",
        }
        mock_llm_router.return_value = mock_llm

        resp = public_client.post(
            "/api/public/chatbot/query",
            json={"query": "hello"},
            headers={"X-API-Key": "fik_test"},
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["schema_version"], "v1")
        self.assertEqual(data["response"], "public answer")
        mock_record.assert_called()


if __name__ == "__main__":
    unittest.main()
