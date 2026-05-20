#!/usr/bin/env python3
"""Regression tests for cross-source chatbot retrieval deduplication."""

import os
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chatbot_retrieval import retrieve_chatbot_context
from core.chatbot_retrieval_dedup import (
    deduplicate_cross_source_sources,
    source_identity_keys,
)


def _kb_source(doc_id, title="Policy", content="Full policy text.", relevance=0.75):
    preview = content[:200] + "..." if len(content) > 200 else content
    return {
        "type": "knowledge_base",
        "id": doc_id,
        "title": title,
        "content": preview,
        "relevance": relevance,
    }


def _vector_source(doc_id, content="Policy chunk excerpt.", relevance=0.82):
    return {
        "type": "vector",
        "id": doc_id,
        "content": content[:200],
        "relevance": relevance,
    }


def _faq_source(faq_id="faq_1", confidence=0.9):
    return {
        "type": "faq",
        "id": faq_id,
        "question": "Refund policy?",
        "answer": "30-day refunds.",
        "confidence": confidence,
    }


class TestSourceIdentityKeys(unittest.TestCase):
    def test_kb_and_vector_share_document_id_key(self):
        kb_keys = source_identity_keys(_kb_source("doc-shared"))
        vector_keys = source_identity_keys(_vector_source("doc-shared"))
        self.assertEqual(kb_keys, ["id:doc-shared"])
        self.assertEqual(vector_keys, ["id:doc-shared"])
        self.assertEqual(kb_keys, vector_keys)


class TestDeduplicateCrossSourceSources(unittest.TestCase):
    def test_kb_and_vector_same_parent_collapses_to_one(self):
        sources = [
            _kb_source("doc-a", relevance=0.70),
            _vector_source("doc-a", relevance=0.78),
        ]
        result = deduplicate_cross_source_sources(sources, strong_vector_gap=0.15)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "knowledge_base")
        self.assertEqual(result[0]["id"], "doc-a")

    def test_different_documents_remain(self):
        sources = [
            _kb_source("doc-a"),
            _vector_source("doc-b"),
            _kb_source("doc-c"),
        ]
        result = deduplicate_cross_source_sources(sources)
        self.assertEqual([item["id"] for item in result], ["doc-a", "doc-b", "doc-c"])

    def test_faq_is_not_removed(self):
        sources = [
            _faq_source("faq_1"),
            _kb_source("doc-a"),
            _vector_source("doc-a"),
        ]
        result = deduplicate_cross_source_sources(sources)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["type"], "faq")
        self.assertEqual(result[1]["type"], "knowledge_base")

    def test_vector_only_remains_without_kb_duplicate(self):
        sources = [_vector_source("doc-only", relevance=0.91)]
        result = deduplicate_cross_source_sources(sources)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "vector")
        self.assertEqual(result[0]["id"], "doc-only")

    def test_ordering_is_deterministic(self):
        sources = [
            _kb_source("doc-b", relevance=0.6),
            _vector_source("doc-b", relevance=0.65),
            _kb_source("doc-a", relevance=0.8),
            _vector_source("doc-c", relevance=0.7),
        ]
        first = deduplicate_cross_source_sources(sources)
        second = deduplicate_cross_source_sources(sources)
        self.assertEqual(first, second)
        self.assertEqual([item["id"] for item in first], ["doc-b", "doc-a", "doc-c"])

    def test_strong_vector_score_prefers_vector_over_kb(self):
        sources = [
            _kb_source("doc-a", relevance=0.60),
            _vector_source("doc-a", relevance=0.80),
        ]
        result = deduplicate_cross_source_sources(sources, strong_vector_gap=0.15)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "vector")
        self.assertEqual(result[0]["relevance"], 0.80)

    def test_public_source_shape_unchanged(self):
        sources = [
            _faq_source(),
            _kb_source("doc-a"),
            _vector_source("doc-a"),
        ]
        result = deduplicate_cross_source_sources(sources)
        faq = result[0]
        kb = result[1]
        self.assertEqual(set(faq.keys()), {"type", "id", "question", "answer", "confidence"})
        self.assertEqual(set(kb.keys()), {"type", "id", "title", "content", "relevance"})


class TestRetrieveChatbotContextCrossSourceDedup(unittest.TestCase):
    @patch("core.chatbot_retrieval.get_feature_flags")
    @patch("core.chatbot_retrieval.get_vector_search")
    @patch("core.chatbot_retrieval.knowledge_base")
    @patch("core.chatbot_retrieval.faq_system")
    def test_kb_vector_duplicate_collapsed_in_retrieval(
        self, mock_faq, mock_kb, mock_get_vs, mock_flags
    ):
        mock_flags.return_value.is_enabled.return_value = True
        mock_faq.search_faqs.return_value = Mock(success=True, matches=[])

        mock_doc = Mock()
        mock_doc.id = "doc-shared"
        mock_doc.title = "Refund Policy"
        mock_doc.content = "We offer 30-day refunds on all plans."
        kb_entry = Mock(document=mock_doc, relevance_score=0.72)
        mock_kb.search.return_value = Mock(success=True, results=[kb_entry])

        vs = MagicMock()
        vs.search_similar.return_value = [
            {
                "id": "doc-shared__chunk_0",
                "document": "30-day refunds on all plans.",
                "similarity": 0.79,
                "metadata": {
                    "parent_doc_id": "doc-shared",
                    "document_id": "doc-shared",
                    "chunk_index": 0,
                    "total_chunks": 2,
                },
            }
        ]
        mock_get_vs.return_value = vs

        result = retrieve_chatbot_context("refund policy", "tenant_a", 1)

        self.assertEqual(result.source_count, 1)
        self.assertEqual(len(result.sources), 1)
        self.assertEqual(result.sources[0]["type"], "knowledge_base")
        self.assertEqual(result.sources[0]["id"], "doc-shared")
        self.assertEqual(result.snippets[0]["type"], "knowledge_base")
        self.assertIn("refund", result.context_text.lower())

    @patch("core.chatbot_retrieval.get_feature_flags")
    @patch("core.chatbot_retrieval.get_vector_search")
    @patch("core.chatbot_retrieval.knowledge_base")
    @patch("core.chatbot_retrieval.faq_system")
    def test_vector_only_when_kb_misses_same_doc(
        self, mock_faq, mock_kb, mock_get_vs, mock_flags
    ):
        mock_flags.return_value.is_enabled.return_value = True
        mock_faq.search_faqs.return_value = Mock(success=True, matches=[])
        mock_kb.search.return_value = Mock(success=True, results=[])

        vs = MagicMock()
        vs.search_similar.return_value = [
            {
                "id": "doc-v__chunk_0",
                "document": "Enterprise pricing details.",
                "similarity": 0.88,
                "metadata": {
                    "parent_doc_id": "doc-v",
                    "document_id": "doc-v",
                    "chunk_index": 0,
                    "total_chunks": 1,
                },
            }
        ]
        mock_get_vs.return_value = vs

        result = retrieve_chatbot_context("enterprise pricing", "tenant_a", 1)

        self.assertEqual(result.source_count, 1)
        self.assertEqual(result.sources[0]["type"], "vector")
        self.assertEqual(result.sources[0]["id"], "doc-v")


if __name__ == "__main__":
    unittest.main()
