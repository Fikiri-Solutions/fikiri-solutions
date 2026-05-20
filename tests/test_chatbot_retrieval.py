#!/usr/bin/env python3
"""Unit tests for core.chatbot_retrieval."""

import os
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chatbot_retrieval import (
    RetrievalResult,
    retrieve_chatbot_context,
    retrieval_confidence,
)


class TestChatbotRetrieval(unittest.TestCase):
    @patch("core.chatbot_retrieval.get_feature_flags")
    @patch("core.chatbot_retrieval.get_vector_search")
    @patch("core.chatbot_retrieval.knowledge_base")
    @patch("core.chatbot_retrieval.faq_system")
    def test_retrieve_returns_sources_context_and_confidence(
        self, mock_faq, mock_kb, mock_get_vs, mock_flags
    ):
        mock_flags.return_value.is_enabled.return_value = False

        faq_match = Mock()
        faq_match.faq_entry.id = "faq_1"
        faq_match.faq_entry.question = "Hours?"
        faq_match.faq_entry.answer = "9-5"
        faq_match.confidence = 0.85
        faq_response = Mock(success=True, matches=[faq_match])
        mock_faq.search_faqs.return_value = faq_response

        mock_doc = Mock()
        mock_doc.id = "doc_1"
        mock_doc.title = "Info"
        mock_doc.content = "We are open weekdays."
        kb_entry = Mock(document=mock_doc, relevance_score=0.8)
        mock_kb.search.return_value = Mock(success=True, results=[kb_entry])

        result = retrieve_chatbot_context(
            "What are your hours?",
            "tenant_a",
            42,
        )

        self.assertIsInstance(result, RetrievalResult)
        self.assertEqual(result.source_count, 2)
        self.assertFalse(result.fallback_needed)
        self.assertTrue(result.context_text.strip())
        self.assertGreater(result.retrieval_confidence, 0)
        self.assertEqual(len(result.sources), 2)
        self.assertEqual(result.sources[0]["type"], "faq")
        mock_faq.search_faqs.assert_called_once_with(
            "What are your hours?", max_results=3, user_id=42
        )
        mock_kb.search.assert_called_once()
        filters = mock_kb.search.call_args[1]["filters"]
        self.assertEqual(filters.get("tenant_id"), "tenant_a")

    @patch("core.chatbot_retrieval.get_feature_flags")
    @patch("core.chatbot_retrieval.get_vector_search")
    @patch("core.chatbot_retrieval.knowledge_base")
    @patch("core.chatbot_retrieval.faq_system")
    def test_retrieve_fallback_needed_when_no_context(
        self, mock_faq, mock_kb, mock_get_vs, mock_flags
    ):
        mock_flags.return_value.is_enabled.return_value = False
        mock_faq.search_faqs.return_value = Mock(success=True, matches=[])
        mock_kb.search.return_value = Mock(success=True, results=[])

        result = retrieve_chatbot_context("unknown topic", None, None)

        self.assertTrue(result.fallback_needed)
        self.assertEqual(result.source_count, 0)
        self.assertEqual(result.context_text.strip(), "")
        self.assertEqual(retrieval_confidence([]), 0.0)

    @patch("core.chatbot_retrieval.get_feature_flags")
    @patch("core.chatbot_retrieval.get_vector_search")
    @patch("core.chatbot_retrieval.knowledge_base")
    @patch("core.chatbot_retrieval.faq_system")
    def test_vector_search_uses_tenant_id_when_enabled(
        self, mock_faq, mock_kb, mock_get_vs, mock_flags
    ):
        mock_flags.return_value.is_enabled.return_value = True
        mock_faq.search_faqs.return_value = Mock(success=True, matches=[])
        mock_kb.search.return_value = Mock(success=True, results=[])
        vs = MagicMock()
        vs.search_similar.return_value = []
        mock_get_vs.return_value = vs

        retrieve_chatbot_context("pricing", "tenant_xyz", 1)

        vs.search_similar.assert_called_once_with(
            "pricing",
            top_k=12,
            threshold=0.6,
            tenant_id="tenant_xyz",
        )


if __name__ == "__main__":
    unittest.main()
