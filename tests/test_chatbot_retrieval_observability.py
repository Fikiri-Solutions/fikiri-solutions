#!/usr/bin/env python3
"""Tests for chatbot retrieval observability (debug metadata + structured logs)."""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("SKIP_HEAVY_DEP_CHECKS", "true")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask

from core.chatbot_retrieval import retrieve_chatbot_context
from core.chatbot_smart_faq_api import chatbot_bp


def _vector_hit(parent_id, chunk_index, similarity, text):
    return {
        "id": f"{parent_id}__chunk_{chunk_index}",
        "document": text,
        "similarity": similarity,
        "metadata": {
            "parent_doc_id": parent_id,
            "document_id": parent_id,
            "chunk_index": chunk_index,
            "total_chunks": 4,
        },
    }


class TestRetrievalDebugMetadata(unittest.TestCase):
    @patch("core.chatbot_retrieval.get_feature_flags")
    @patch("core.chatbot_retrieval.get_vector_search")
    @patch("core.chatbot_retrieval.knowledge_base")
    @patch("core.chatbot_retrieval.faq_system")
    def test_retrieval_debug_contains_expected_counts(
        self, mock_faq, mock_kb, mock_get_vs, mock_flags
    ):
        mock_flags.return_value.is_enabled.return_value = True

        faq_match = Mock()
        faq_match.faq_entry.id = "faq_1"
        faq_match.faq_entry.question = "Hours?"
        faq_match.faq_entry.answer = "9-5"
        faq_match.confidence = 0.85
        mock_faq.search_faqs.return_value = Mock(success=True, matches=[faq_match])

        mock_doc = Mock()
        mock_doc.id = "doc-shared"
        mock_doc.title = "Policy"
        mock_doc.content = "Shared policy content for testing."
        kb_entry = Mock(document=mock_doc, relevance_score=0.72)
        mock_kb.search.return_value = Mock(success=True, results=[kb_entry])

        vs = MagicMock()
        vs.search_similar.return_value = [
            _vector_hit("doc-shared", 0, 0.95, "chunk 0"),
            _vector_hit("doc-shared", 1, 0.94, "chunk 1"),
            _vector_hit("doc-other", 0, 0.80, "other doc"),
        ]
        mock_get_vs.return_value = vs

        result = retrieve_chatbot_context(
            "policy question",
            "tenant_a",
            1,
            correlation_id="corr-test-1",
        )

        debug = result.retrieval_debug
        self.assertEqual(debug["raw_faq_count"], 1)
        self.assertEqual(debug["raw_kb_count"], 1)
        self.assertEqual(debug["raw_vector_count"], 3)
        self.assertEqual(debug["post_vector_diversity_count"], 3)
        self.assertEqual(debug["post_cross_source_dedup_count"], 3)
        self.assertEqual(debug["final_source_count"], 3)
        self.assertEqual(debug["collapsed_duplicate_count"], 2)
        self.assertTrue(debug["context_char_count"] > 0)
        self.assertFalse(debug["fallback_needed"])
        self.assertGreater(debug["retrieval_confidence"], 0)
        self.assertEqual(debug["vector_fetch_top_k"], 12)
        self.assertEqual(debug["max_chunks_per_parent"], 2)
        self.assertTrue(debug["vector_enabled"])
        self.assertTrue(debug["vector_search_enabled"])
        self.assertIsInstance(debug["latency_ms"], int)

    @patch("core.chatbot_retrieval.get_feature_flags")
    @patch("core.chatbot_retrieval.get_vector_search")
    @patch("core.chatbot_retrieval.knowledge_base")
    @patch("core.chatbot_retrieval.faq_system")
    def test_vector_diversity_count_recorded_after_raw_fetch(
        self, mock_faq, mock_kb, mock_get_vs, mock_flags
    ):
        mock_flags.return_value.is_enabled.return_value = True
        mock_faq.search_faqs.return_value = Mock(success=True, matches=[])
        mock_kb.search.return_value = Mock(success=True, results=[])

        vs = MagicMock()
        vs.search_similar.return_value = [
            _vector_hit("doc-a", 0, 0.95, "a0"),
            _vector_hit("doc-a", 1, 0.94, "a1"),
            _vector_hit("doc-a", 2, 0.70, "a2"),
        ]
        mock_get_vs.return_value = vs

        result = retrieve_chatbot_context("hours", "tenant_a", 1)

        self.assertEqual(result.retrieval_debug["raw_vector_count"], 3)
        self.assertEqual(result.retrieval_debug["post_vector_diversity_count"], 2)

    @patch("core.chatbot_retrieval.get_feature_flags")
    @patch("core.chatbot_retrieval.get_vector_search")
    @patch("core.chatbot_retrieval.knowledge_base")
    @patch("core.chatbot_retrieval.faq_system")
    def test_dedup_collapsed_count_recorded_for_kb_vector_duplicate(
        self, mock_faq, mock_kb, mock_get_vs, mock_flags
    ):
        mock_flags.return_value.is_enabled.return_value = True
        mock_faq.search_faqs.return_value = Mock(success=True, matches=[])

        mock_doc = Mock()
        mock_doc.id = "doc-shared"
        mock_doc.title = "Refund Policy"
        mock_doc.content = "30-day refunds on all plans."
        mock_kb.search.return_value = Mock(
            success=True,
            results=[Mock(document=mock_doc, relevance_score=0.72)],
        )

        vs = MagicMock()
        vs.search_similar.return_value = [_vector_hit("doc-shared", 0, 0.79, "refund chunk")]
        mock_get_vs.return_value = vs

        result = retrieve_chatbot_context("refund policy", "tenant_a", 1)

        self.assertEqual(result.retrieval_debug["collapsed_duplicate_count"], 1)
        self.assertEqual(result.retrieval_debug["final_source_count"], 1)

    @patch("core.chatbot_retrieval.get_feature_flags")
    @patch("core.chatbot_retrieval.get_vector_search")
    @patch("core.chatbot_retrieval.knowledge_base")
    @patch("core.chatbot_retrieval.faq_system")
    def test_structured_log_emitted_without_private_content(
        self, mock_faq, mock_kb, mock_get_vs, mock_flags
    ):
        mock_flags.return_value.is_enabled.return_value = False

        faq_match = Mock()
        faq_match.faq_entry.id = "faq_1"
        faq_match.faq_entry.question = "Secret user question?"
        faq_match.faq_entry.answer = "PRIVATE_ANSWER_TEXT_SHOULD_NOT_LOG"
        faq_match.confidence = 0.9
        mock_faq.search_faqs.return_value = Mock(success=True, matches=[faq_match])
        mock_kb.search.return_value = Mock(success=True, results=[])

        with patch("core.chatbot_retrieval.logger.info") as mock_log_info:
            retrieve_chatbot_context(
                "SECRET_USER_QUERY_SHOULD_NOT_LOG",
                "tenant_a",
                99,
                correlation_id="corr-log-1",
            )

        mock_log_info.assert_called_once()
        message = mock_log_info.call_args[0][0]
        extra = mock_log_info.call_args[1].get("extra", {})
        self.assertEqual(message, "chatbot retrieval completed")
        self.assertEqual(extra.get("event"), "chatbot.retrieval.completed")
        self.assertEqual(extra.get("correlation_id"), "corr-log-1")
        self.assertEqual(extra.get("tenant_id"), "tenant_a")
        self.assertEqual(extra.get("user_id"), 99)
        self.assertIn("raw_faq_count", extra)
        extra_blob = str(extra)
        self.assertNotIn("SECRET_USER_QUERY_SHOULD_NOT_LOG", extra_blob)
        self.assertNotIn("PRIVATE_ANSWER_TEXT_SHOULD_NOT_LOG", extra_blob)


class TestPreviewDebugExposure(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        self.app.register_blueprint(chatbot_bp)
        self.client = self.app.test_client()

    @patch("core.chatbot_smart_faq_api.generate_chatbot_answer")
    @patch("core.chatbot_smart_faq_api.load_chatbot_config")
    @patch("core.chatbot_smart_faq_api.retrieve_chatbot_context")
    @patch("core.chatbot_smart_faq_api.get_current_user_id")
    def test_preview_debug_false_does_not_expose_retrieval_debug(
        self, mock_uid, mock_retrieve, mock_load_cfg, mock_generate
    ):
        from core.chatbot_config import ChatbotConfig
        from core.chatbot_response_service import ChatbotAnswerResult
        from core.chatbot_retrieval import RetrievalResult

        mock_uid.return_value = 42
        mock_retrieve.return_value = RetrievalResult(
            sources=[],
            snippets=[],
            context_text="",
            retrieval_confidence=0.0,
            fallback_needed=True,
            source_count=0,
            retrieval_debug={"raw_faq_count": 0, "final_source_count": 0},
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

        resp = self.client.post(
            "/api/chatbot/preview-query",
            json={"query": "hello", "debug": False},
        )
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("retrieval_debug", data)

    @patch("core.chatbot_smart_faq_api.generate_chatbot_answer")
    @patch("core.chatbot_smart_faq_api.load_chatbot_config")
    @patch("core.chatbot_smart_faq_api.retrieve_chatbot_context")
    @patch("core.chatbot_smart_faq_api.get_current_user_id")
    def test_preview_debug_true_exposes_retrieval_debug(
        self, mock_uid, mock_retrieve, mock_load_cfg, mock_generate
    ):
        from core.chatbot_config import ChatbotConfig
        from core.chatbot_response_service import ChatbotAnswerResult
        from core.chatbot_retrieval import RetrievalResult

        debug_payload = {
            "raw_faq_count": 1,
            "raw_kb_count": 1,
            "raw_vector_count": 3,
            "post_vector_diversity_count": 2,
            "post_cross_source_dedup_count": 2,
            "final_source_count": 2,
            "collapsed_duplicate_count": 0,
        }
        mock_uid.return_value = 42
        mock_retrieve.return_value = RetrievalResult(
            sources=[{"type": "faq", "id": "f1", "question": "Q", "answer": "A", "confidence": 0.9}],
            snippets=[],
            context_text="FAQ: A",
            retrieval_confidence=0.9,
            fallback_needed=False,
            source_count=1,
            retrieval_debug=debug_payload,
        )
        mock_load_cfg.return_value = ChatbotConfig()
        mock_generate.return_value = ChatbotAnswerResult(
            answer="answer",
            confidence=0.8,
            llm_confidence=0.7,
            combined_confidence=0.8,
            fallback_used=False,
            escalation_recommended=False,
            llm_trace_id="trace",
            retrieval_confidence=0.9,
        )

        resp = self.client.post(
            "/api/chatbot/preview-query",
            json={"query": "hello", "debug": True},
        )
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data["retrieval_debug"], debug_payload)


class TestPublicApiDebugNotExposed(unittest.TestCase):
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
    def test_public_query_does_not_expose_retrieval_debug(
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
        from core.chatbot_config import ChatbotConfig
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
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data["schema_version"], "v1")
        self.assertNotIn("retrieval_debug", data)


if __name__ == "__main__":
    unittest.main()
