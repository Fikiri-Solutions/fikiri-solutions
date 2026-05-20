#!/usr/bin/env python3
"""Regression tests for chunked KB vector cleanup lifecycle."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chatbot_vector_chunk_cleanup import (
    collect_chunk_vector_ids,
    delete_kb_chunk_vectors,
    kb_vector_metadata_fields,
)
from core.chatbot_vector_chunk_ingestion import ingest_kb_text_to_vector_store


class TestChunkVectorCleanup(unittest.TestCase):
    def test_collect_prefers_stored_chunk_vector_ids(self):
        ids = collect_chunk_vector_ids(
            "doc-1",
            stored_chunk_ids=["doc-1__chunk_0", "doc-1__chunk_1"],
            previous_chunk_count=5,
            prior_vector_id="legacy",
        )
        self.assertEqual(ids[:2], ["doc-1__chunk_0", "doc-1__chunk_1"])
        self.assertIn("legacy", ids)
        self.assertIn("doc-1", ids)

    def test_missing_metadata_uses_bounded_chunk_suffixes(self):
        ids = collect_chunk_vector_ids("doc-2", max_chunks=3)
        self.assertIn("doc-2", ids)
        self.assertIn("doc-2__chunk_0", ids)
        self.assertIn("doc-2__chunk_2", ids)
        self.assertNotIn("doc-2__chunk_3", ids)

    def test_delete_kb_chunk_vectors_swallows_delete_errors(self):
        vs = MagicMock()
        vs.use_pinecone = True
        vs.delete_document_by_id.side_effect = [True, Exception("boom"), False]
        result = delete_kb_chunk_vectors(
            vs,
            "doc-3",
            stored_chunk_ids=["doc-3__chunk_0", "doc-3__chunk_1", "doc-3__chunk_2"],
            use_pinecone=True,
        )
        self.assertEqual(result["attempted"], 4)
        self.assertGreaterEqual(result["deleted"], 1)
        self.assertGreaterEqual(result["errors"], 1)

    def test_delete_local_int_vectors_in_descending_order(self):
        vs = MagicMock()
        vs.use_pinecone = False
        deleted = []

        def _delete(doc_id):
            deleted.append(doc_id)
            return True

        vs.delete_document.side_effect = _delete
        delete_kb_chunk_vectors(
            vs,
            "doc-4",
            stored_chunk_ids=[10, 11, 12],
            use_pinecone=False,
        )
        self.assertEqual(deleted, [12, 11, 10])

    def test_kb_vector_metadata_fields(self):
        fields = kb_vector_metadata_fields([10, 11], 10)
        self.assertEqual(fields["vector_id"], 10)
        self.assertEqual(fields["chunk_vector_ids"], [10, 11])
        self.assertEqual(fields["chunk_count"], 2)


class TestRevectorizeChunkLifecycle(unittest.TestCase):
    def test_revectorize_shorter_doc_deletes_stale_chunk_ids(self):
        vs = MagicMock()
        vs.use_pinecone = True
        vs.upsert_document.return_value = True
        deleted_ids = []

        def _delete(vector_id):
            deleted_ids.append(vector_id)
            return True

        vs.delete_document_by_id.side_effect = _delete

        long_text = ("Long policy detail sentence. " * 60 + "\n\n") * 5
        ingest_kb_text_to_vector_store(
            vs,
            text=long_text,
            parent_doc_id="doc-rv",
            base_metadata={"type": "knowledge_base", "tenant_id": "t1"},
            use_pinecone=True,
            max_chars=250,
            overlap_chars=20,
        )
        self.assertGreater(vs.upsert_document.call_count, 2)
        prior_ids = [call[0][0] for call in vs.upsert_document.call_args_list]

        ingest_kb_text_to_vector_store(
            vs,
            text="Short updated answer.",
            parent_doc_id="doc-rv",
            base_metadata={"type": "knowledge_base", "tenant_id": "t1"},
            use_pinecone=True,
            cleanup_metadata={
                "chunk_vector_ids": prior_ids,
                "chunk_count": len(prior_ids),
                "vector_id": prior_ids[0],
            },
        )

        for stale_id in prior_ids:
            self.assertIn(stale_id, deleted_ids)
        self.assertEqual(vs.upsert_document.call_args_list[-1][0][0], "doc-rv")

    def test_short_document_still_single_vector_after_cleanup(self):
        vs = MagicMock()
        vs.use_pinecone = False
        vs.add_document.return_value = 5
        vector_ids, primary = ingest_kb_text_to_vector_store(
            vs,
            text="Tiny doc.",
            parent_doc_id="doc-short",
            base_metadata={"type": "knowledge_base"},
            use_pinecone=False,
            cleanup_metadata={
                "chunk_vector_ids": ["doc-short__chunk_0", "doc-short__chunk_1"],
                "chunk_count": 2,
                "vector_id": "doc-short__chunk_0",
            },
        )
        self.assertEqual(vector_ids, [5])
        self.assertEqual(primary, 5)
        vs.add_document.assert_called_once()


class TestKBDeleteChunkLifecycle(unittest.TestCase):
    @patch("core.knowledge_base_system._get_vector_search")
    def test_kb_delete_removes_all_chunk_vectors(self, mock_get_vs):
        from core.knowledge_base_system import KnowledgeBaseSystem, KnowledgeDocument
        from core.knowledge_base_system import DocumentType, ContentFormat
        from datetime import datetime

        kb = KnowledgeBaseSystem()
        doc_id = "doc-del"
        doc = KnowledgeDocument(
            id=doc_id,
            title="Delete me",
            content="Content",
            summary="Summary",
            document_type=DocumentType.ARTICLE,
            format=ContentFormat.TEXT,
            tags=[],
            keywords=[],
            category="test",
            author="test",
            version="1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={
                "vector_id": "doc-del__chunk_0",
                "chunk_vector_ids": ["doc-del__chunk_0", "doc-del__chunk_1", "doc-del__chunk_2"],
                "chunk_count": 3,
            },
        )
        kb.documents[doc_id] = doc
        kb.search_index = {}

        mock_vs = MagicMock()
        mock_vs.use_pinecone = True
        mock_vs.delete_document_by_id.return_value = True
        mock_get_vs.return_value = mock_vs

        self.assertTrue(kb.delete_document(doc_id))
        deleted = [call[0][0] for call in mock_vs.delete_document_by_id.call_args_list]
        self.assertIn("doc-del__chunk_0", deleted)
        self.assertIn("doc-del__chunk_1", deleted)
        self.assertIn("doc-del__chunk_2", deleted)


class TestRevectorizeRouteMetadata(unittest.TestCase):
    @patch("core.chatbot_smart_faq_api.ingest_kb_text_to_vector_store_tracked")
    def test_ingest_kb_vectors_passes_cleanup_metadata_on_revectorize(self, mock_ingest):
        from core.chatbot_smart_faq_api import _ingest_kb_vectors

        mock_ingest.return_value = (["doc-route"], "doc-route")
        vs = MagicMock()
        vs.use_pinecone = False
        cleanup = {
            "vector_id": "doc-route__chunk_0",
            "chunk_vector_ids": ["doc-route__chunk_0", "doc-route__chunk_1"],
            "chunk_count": 2,
        }
        _ingest_kb_vectors(
            vs,
            "Updated text",
            "doc-route",
            {"type": "knowledge_base"},
            replace_existing=True,
            cleanup_metadata=cleanup,
        )
        mock_ingest.assert_called_once()
        self.assertEqual(mock_ingest.call_args.kwargs["cleanup_metadata"], cleanup)


class TestPublicRetrievalAfterRevectorize(unittest.TestCase):
    @patch("core.chatbot_retrieval.get_feature_flags")
    @patch("core.chatbot_retrieval.get_vector_search")
    @patch("core.chatbot_retrieval.knowledge_base")
    @patch("core.chatbot_retrieval.faq_system")
    def test_retrieval_does_not_surface_stale_chunk_content(
        self, mock_faq, mock_kb, mock_get_vs, mock_flags
    ):
        from core.chatbot_retrieval import retrieve_chatbot_context

        mock_flags.return_value.is_enabled.return_value = True
        mock_faq.search_faqs.return_value = MagicMock(success=True, matches=[])
        mock_kb.search.return_value = MagicMock(success=True, results=[])

        mock_vs = MagicMock()
        mock_vs.search_similar.return_value = [
            {
                "document": "Current short answer only.",
                "similarity": 0.9,
                "metadata": {
                    "parent_doc_id": "doc-live",
                    "document_id": "doc-live",
                    "chunk_index": 0,
                    "total_chunks": 1,
                    "tenant_id": "tenant_a",
                },
                "id": "doc-live",
            }
        ]
        mock_get_vs.return_value = mock_vs

        result = retrieve_chatbot_context("current answer", "tenant_a", 1)

        self.assertFalse(result.fallback_needed)
        self.assertEqual(result.source_count, 1)
        self.assertNotIn("stale orphan chunk", result.context_text.lower())
        self.assertIn("Current short answer", result.context_text)


if __name__ == "__main__":
    unittest.main()
