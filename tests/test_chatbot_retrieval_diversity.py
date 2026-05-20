#!/usr/bin/env python3
"""Regression tests for chatbot retrieval chunk diversity."""

import os
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chatbot_retrieval import retrieve_chatbot_context
from core.chatbot_retrieval_diversity import diversify_vector_hits


def _vector_hit(parent_id, chunk_index, similarity, text):
    return {
        "id": f"{parent_id}__chunk_{chunk_index}",
        "document": text,
        "similarity": similarity,
        "metadata": {
            "parent_doc_id": parent_id,
            "document_id": parent_id,
            "chunk_index": chunk_index,
            "total_chunks": 5,
            "tenant_id": "tenant_a",
        },
    }


class TestDiversifyVectorHits(unittest.TestCase):
    def test_collapses_excessive_chunks_from_same_parent(self):
        hits = [
            _vector_hit("doc-a", 0, 0.95, "chunk 0"),
            _vector_hit("doc-a", 1, 0.94, "chunk 1"),
            _vector_hit("doc-a", 2, 0.70, "chunk 2"),
            _vector_hit("doc-a", 3, 0.69, "chunk 3"),
        ]
        result = diversify_vector_hits(hits, max_per_parent=2, adjacent_score_gap=0.08, max_results=3)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["metadata"]["chunk_index"], 0)
        self.assertEqual(result[1]["metadata"]["chunk_index"], 1)

    def test_best_scoring_chunk_retained(self):
        hits = [
            _vector_hit("doc-a", 2, 0.99, "best"),
            _vector_hit("doc-a", 0, 0.60, "weak"),
        ]
        result = diversify_vector_hits(hits, max_per_parent=1, max_results=3)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["metadata"]["chunk_index"], 2)
        self.assertEqual(result[0]["document"], "best")

    def test_adjacent_supporting_chunk_retained_when_score_gap_small(self):
        hits = [
            _vector_hit("doc-a", 1, 0.90, "primary"),
            _vector_hit("doc-a", 2, 0.87, "support"),
            _vector_hit("doc-a", 4, 0.86, "distant"),
        ]
        result = diversify_vector_hits(hits, max_per_parent=2, adjacent_score_gap=0.08, max_results=3)
        indexes = [item["metadata"]["chunk_index"] for item in result]
        self.assertEqual(indexes, [1, 2])

    def test_different_documents_still_surface_together(self):
        hits = [
            _vector_hit("doc-a", 0, 0.92, "a0"),
            _vector_hit("doc-a", 1, 0.91, "a1"),
            _vector_hit("doc-b", 0, 0.88, "b0"),
            _vector_hit("doc-c", 0, 0.85, "c0"),
        ]
        result = diversify_vector_hits(hits, max_per_parent=1, adjacent_score_gap=0.08, max_results=3)
        parents = [item["metadata"]["parent_doc_id"] for item in result]
        self.assertEqual(parents, ["doc-a", "doc-b", "doc-c"])

    def test_ordering_is_deterministic(self):
        hits = [
            _vector_hit("doc-b", 0, 0.80, "b"),
            _vector_hit("doc-a", 0, 0.80, "a"),
            _vector_hit("doc-c", 0, 0.90, "c"),
        ]
        first = diversify_vector_hits(hits, max_per_parent=1, max_results=3)
        second = diversify_vector_hits(hits, max_per_parent=1, max_results=3)
        self.assertEqual(
            [item["metadata"]["parent_doc_id"] for item in first],
            [item["metadata"]["parent_doc_id"] for item in second],
        )
        self.assertEqual([item["metadata"]["parent_doc_id"] for item in first], ["doc-c", "doc-a", "doc-b"])

    def test_single_chunk_document_unchanged(self):
        hits = [_vector_hit("doc-single", 0, 0.91, "only chunk")]
        result = diversify_vector_hits(hits, max_per_parent=2, max_results=3)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["document"], "only chunk")


class TestRetrieveChatbotContextDiversity(unittest.TestCase):
    @patch("core.chatbot_retrieval.get_feature_flags")
    @patch("core.chatbot_retrieval.get_vector_search")
    @patch("core.chatbot_retrieval.knowledge_base")
    @patch("core.chatbot_retrieval.faq_system")
    def test_faq_results_unaffected_by_vector_diversity(
        self, mock_faq, mock_kb, mock_get_vs, mock_flags
    ):
        mock_flags.return_value.is_enabled.return_value = True

        faq_match = Mock()
        faq_match.faq_entry.id = "faq_1"
        faq_match.faq_entry.question = "Hours?"
        faq_match.faq_entry.answer = "9-5"
        faq_match.confidence = 0.85
        mock_faq.search_faqs.return_value = Mock(success=True, matches=[faq_match])
        mock_kb.search.return_value = Mock(success=True, results=[])

        vs = MagicMock()
        vs.search_similar.return_value = [
            _vector_hit("doc-a", 0, 0.95, "a0"),
            _vector_hit("doc-a", 1, 0.94, "a1"),
            _vector_hit("doc-a", 2, 0.70, "a2"),
        ]
        mock_get_vs.return_value = vs

        result = retrieve_chatbot_context("hours", "tenant_a", 1)

        self.assertEqual(result.sources[0]["type"], "faq")
        self.assertEqual(result.sources[0]["id"], "faq_1")
        vector_sources = [source for source in result.sources if source["type"] == "vector"]
        self.assertLessEqual(len(vector_sources), 2)
        self.assertEqual(vector_sources[0]["id"], "doc-a")

    @patch("core.chatbot_retrieval.get_feature_flags")
    @patch("core.chatbot_retrieval.get_vector_search")
    @patch("core.chatbot_retrieval.knowledge_base")
    @patch("core.chatbot_retrieval.faq_system")
    def test_vector_search_uses_expanded_fetch_top_k(
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
