#!/usr/bin/env python3
"""
KB ↔ Vector index sync tests (docs/CRUD_RAG_ARCHITECTURE.md).
Ensures update_document and delete_document sync to vector when vector_id is present,
and that KB CRUD succeeds when vector backend fails or vector_id is missing.
"""

import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_doc(doc_id, content, metadata=None, title="Title"):
    from core.knowledge_base_system import KnowledgeDocument, DocumentType, ContentFormat

    return KnowledgeDocument(
        id=doc_id,
        title=title,
        content=content,
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
        metadata=metadata or {},
    )


class TestKBVectorSync(unittest.TestCase):
    """KB update/delete → vector sync and fallbacks."""

    @patch("core.knowledge_base_system._get_vector_search")
    def test_kb_update_rechunks_when_vector_id_present(self, mock_get_vs):
        from core.knowledge_base_system import KnowledgeBaseSystem

        kb = KnowledgeBaseSystem()
        doc_id = "test_sync_doc"
        kb.documents[doc_id] = _make_doc(
            doc_id,
            "Old content",
            metadata={"vector_id": 42, "chunk_vector_ids": [42], "chunk_count": 1},
        )
        kb.search_index = {}

        mock_vs = MagicMock()
        mock_vs.use_pinecone = False
        mock_vs.add_document.return_value = 55
        mock_vs.delete_document.return_value = True
        mock_get_vs.return_value = mock_vs

        result = kb.update_document(doc_id, {"title": "New Title", "content": "New content"})

        self.assertTrue(result)
        mock_get_vs.assert_called_once()
        mock_vs.add_document.assert_called_once()
        self.assertEqual(kb.documents[doc_id].metadata["vector_id"], 55)
        self.assertEqual(kb.documents[doc_id].metadata["chunk_vector_ids"], [55])
        self.assertEqual(kb.documents[doc_id].metadata["chunk_count"], 1)

    @patch("core.knowledge_base_system._get_vector_search")
    def test_kb_delete_deletes_vector_when_vector_id_present(self, mock_get_vs):
        from core.knowledge_base_system import KnowledgeBaseSystem

        kb = KnowledgeBaseSystem()
        doc_id = "test_delete_doc"
        kb.documents[doc_id] = _make_doc(doc_id, "Content", metadata={"vector_id": 99})
        kb.search_index = {}

        mock_vs = MagicMock()
        mock_vs.use_pinecone = False
        mock_vs.delete_document_by_id.return_value = True
        mock_vs.delete_document.return_value = True
        mock_get_vs.return_value = mock_vs

        result = kb.delete_document(doc_id)

        self.assertTrue(result)
        mock_get_vs.assert_called_once()
        self.assertTrue(
            mock_vs.delete_document.called or mock_vs.delete_document_by_id.called
        )
        self.assertNotIn(doc_id, kb.documents)

    @patch("core.chatbot_vector_chunk_ingestion.sync_kb_document_vectors")
    @patch("core.knowledge_base_system._get_vector_search")
    def test_kb_update_logs_and_succeeds_when_vector_backend_fails(
        self, mock_get_vs, mock_sync
    ):
        from core.knowledge_base_system import KnowledgeBaseSystem

        kb = KnowledgeBaseSystem()
        doc_id = "test_fail_doc"
        kb.documents[doc_id] = _make_doc(doc_id, "Content", metadata={"vector_id": 1})
        kb.search_index = {}

        mock_get_vs.return_value = MagicMock()
        mock_sync.side_effect = Exception("Vector backend down")

        result = kb.update_document(doc_id, {"title": "Updated"})

        self.assertTrue(result)
        self.assertEqual(kb.documents[doc_id].title, "Updated")

    @patch("core.knowledge_base_system._get_vector_search")
    def test_kb_update_self_heals_when_vector_id_missing(self, mock_get_vs):
        from core.knowledge_base_system import KnowledgeBaseSystem

        kb = KnowledgeBaseSystem()
        doc_id = "test_selfheal_doc"
        doc = _make_doc(doc_id, "Content", metadata={})
        kb.documents[doc_id] = doc
        kb.search_index = {}

        mock_vs = MagicMock()
        mock_vs.use_pinecone = False
        mock_vs.add_document.return_value = 777
        mock_get_vs.return_value = mock_vs

        result = kb.update_document(doc_id, {"content": "Updated content"})

        self.assertTrue(result)
        mock_vs.add_document.assert_called_once()
        self.assertEqual(doc.metadata.get("vector_id"), 777)
        self.assertEqual(doc.metadata.get("chunk_count"), 1)


class TestKBUpdateChunkLifecycle(unittest.TestCase):
    @patch("core.knowledge_base_system._get_vector_search")
    def test_update_long_doc_replaces_old_chunk_vectors(self, mock_get_vs):
        from core.knowledge_base_system import KnowledgeBaseSystem

        kb = KnowledgeBaseSystem()
        doc_id = "doc-long-edit"
        long_text = ("Policy detail sentence. " * 50 + "\n\n") * 4
        kb.documents[doc_id] = _make_doc(
            doc_id,
            long_text,
            metadata={
                "vector_id": "doc-long-edit__chunk_0",
                "chunk_vector_ids": [
                    "doc-long-edit__chunk_0",
                    "doc-long-edit__chunk_1",
                    "doc-long-edit__chunk_2",
                ],
                "chunk_count": 3,
                "tenant_id": "tenant_a",
                "user_id": 7,
            },
        )
        kb.search_index = {}

        vs = MagicMock()
        vs.use_pinecone = True
        vs.delete_document_by_id.return_value = True
        vs.upsert_document.return_value = True
        mock_get_vs.return_value = vs

        updated_long = long_text + "\n\nExtra appendix paragraph."
        self.assertTrue(kb.update_document(doc_id, {"content": updated_long}))

        deleted = [call[0][0] for call in vs.delete_document_by_id.call_args_list]
        self.assertIn("doc-long-edit__chunk_2", deleted)
        self.assertGreater(vs.upsert_document.call_count, 2)
        meta = kb.documents[doc_id].metadata
        self.assertEqual(meta["tenant_id"], "tenant_a")
        self.assertEqual(meta["user_id"], 7)
        self.assertGreater(meta["chunk_count"], 1)
        self.assertEqual(len(meta["chunk_vector_ids"]), meta["chunk_count"])

    @patch("core.knowledge_base_system._get_vector_search")
    def test_update_long_to_short_doc_removes_stale_chunks(self, mock_get_vs):
        from core.knowledge_base_system import KnowledgeBaseSystem

        kb = KnowledgeBaseSystem()
        doc_id = "doc-shrink"
        kb.documents[doc_id] = _make_doc(
            doc_id,
            ("Long body. " * 200) + "\n\n" + ("More body. " * 200),
            metadata={
                "vector_id": "doc-shrink__chunk_0",
                "chunk_vector_ids": [
                    "doc-shrink__chunk_0",
                    "doc-shrink__chunk_1",
                    "doc-shrink__chunk_2",
                ],
                "chunk_count": 3,
            },
        )
        kb.search_index = {}

        vs = MagicMock()
        vs.use_pinecone = True
        vs.delete_document_by_id.return_value = True
        vs.upsert_document.return_value = True
        mock_get_vs.return_value = vs

        self.assertTrue(kb.update_document(doc_id, {"content": "Short answer."}))

        deleted = [call[0][0] for call in vs.delete_document_by_id.call_args_list]
        self.assertIn("doc-shrink__chunk_2", deleted)
        meta = kb.documents[doc_id].metadata
        self.assertEqual(meta["chunk_count"], 1)
        self.assertEqual(meta["chunk_vector_ids"], ["doc-shrink"])
        self.assertEqual(vs.upsert_document.call_args_list[-1][0][0], "doc-shrink")

    @patch("core.knowledge_base_system._get_vector_search")
    def test_update_short_to_long_doc_creates_multiple_chunks(self, mock_get_vs):
        from core.knowledge_base_system import KnowledgeBaseSystem

        kb = KnowledgeBaseSystem()
        doc_id = "doc-grow"
        kb.documents[doc_id] = _make_doc(
            doc_id,
            "Brief.",
            metadata={"vector_id": 10, "chunk_vector_ids": [10], "chunk_count": 1},
        )
        kb.search_index = {}

        counter = {"n": 10}

        def _add(**kwargs):
            counter["n"] += 1
            return counter["n"]

        vs = MagicMock()
        vs.use_pinecone = False
        vs.delete_document.return_value = True
        vs.add_document.side_effect = _add
        mock_get_vs.return_value = vs

        long_text = ("Growing section. " * 40 + "\n\n") * 6
        self.assertTrue(kb.update_document(doc_id, {"content": long_text}))

        meta = kb.documents[doc_id].metadata
        self.assertGreater(meta["chunk_count"], 1)
        self.assertEqual(len(meta["chunk_vector_ids"]), meta["chunk_count"])
        self.assertGreater(vs.add_document.call_count, 1)

    @patch("core.chatbot_retrieval.get_feature_flags")
    @patch("core.chatbot_retrieval.get_vector_search")
    @patch("core.chatbot_retrieval.knowledge_base")
    @patch("core.chatbot_retrieval.faq_system")
    def test_retrieval_does_not_surface_stale_chunks_after_kb_update(
        self, mock_faq, mock_kb, mock_get_vs, mock_flags
    ):
        from core.chatbot_retrieval import retrieve_chatbot_context

        mock_flags.return_value.is_enabled.return_value = True
        mock_faq.search_faqs.return_value = MagicMock(success=True, matches=[])
        mock_kb.search.return_value = MagicMock(success=True, results=[])

        mock_vs = MagicMock()
        mock_vs.search_similar.return_value = [
            {
                "document": "Current edited short answer.",
                "similarity": 0.91,
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

        result = retrieve_chatbot_context("edited answer", "tenant_a", 3)

        self.assertFalse(result.fallback_needed)
        self.assertIn("Current edited short answer", result.context_text)
        self.assertNotIn("stale orphan chunk", result.context_text.lower())


if __name__ == "__main__":
    unittest.main()
