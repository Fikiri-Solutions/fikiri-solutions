#!/usr/bin/env python3
"""
KB ↔ Vector index sync tests (docs/CRUD_RAG_ARCHITECTURE.md).
Ensures update_document and delete_document sync to vector when vector_id is present,
and that KB CRUD succeeds when vector backend fails or vector_id is missing.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestKBVectorSync(unittest.TestCase):
    """KB update/delete → vector sync and fallbacks."""

    @patch("core.knowledge_base_system._get_vector_search")
    def test_kb_update_updates_vector_when_vector_id_present(self, mock_get_vs):
        """Update a KB doc with vector_id → vector index is updated."""
        from core.knowledge_base_system import KnowledgeBaseSystem, KnowledgeDocument
        from core.knowledge_base_system import DocumentType, ContentFormat
        from datetime import datetime

        kb = KnowledgeBaseSystem()
        # Ensure we have a doc with vector_id in metadata
        doc_id = "test_sync_doc"
        doc = KnowledgeDocument(
            id=doc_id,
            title="Old Title",
            content="Old content",
            summary="Old summary",
            document_type=DocumentType.ARTICLE,
            format=ContentFormat.TEXT,
            tags=[],
            keywords=[],
            category="test",
            author="test",
            version="1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={"vector_id": 42},
        )
        kb.documents[doc_id] = doc
        kb.search_index = {}

        mock_vs = MagicMock()
        mock_vs.update_document.return_value = True
        mock_get_vs.return_value = mock_vs

        result = kb.update_document(doc_id, {"title": "New Title", "content": "New content"})

        self.assertTrue(result)
        mock_get_vs.assert_called_once()
        mock_vs.update_document.assert_called_once()
        call_args = mock_vs.update_document.call_args
        self.assertEqual(call_args[0][0], 42)
        self.assertIn("New Title", call_args[0][1])
        self.assertIn("New content", call_args[0][1])

    @patch("core.knowledge_base_system._get_vector_search")
    def test_kb_delete_deletes_vector_when_vector_id_present(self, mock_get_vs):
        """Delete a KB doc with vector_id → vector index entry is removed."""
        from core.knowledge_base_system import KnowledgeBaseSystem, KnowledgeDocument
        from core.knowledge_base_system import DocumentType, ContentFormat
        from datetime import datetime

        kb = KnowledgeBaseSystem()
        doc_id = "test_delete_doc"
        doc = KnowledgeDocument(
            id=doc_id,
            title="To Delete",
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
            metadata={"vector_id": 99},
        )
        kb.documents[doc_id] = doc
        kb.search_index = {}

        mock_vs = MagicMock()
        mock_vs.delete_document.return_value = True
        mock_get_vs.return_value = mock_vs

        result = kb.delete_document(doc_id)

        self.assertTrue(result)
        mock_get_vs.assert_called_once()
        mock_vs.delete_document.assert_called_once_with(99)
        self.assertNotIn(doc_id, kb.documents)

    @patch("core.knowledge_base_system._get_vector_search")
    def test_kb_update_logs_and_succeeds_when_vector_backend_fails(self, mock_get_vs):
        """KB update still succeeds when vector update_document raises."""
        from core.knowledge_base_system import KnowledgeBaseSystem, KnowledgeDocument
        from core.knowledge_base_system import DocumentType, ContentFormat
        from datetime import datetime

        kb = KnowledgeBaseSystem()
        doc_id = "test_fail_doc"
        doc = KnowledgeDocument(
            id=doc_id,
            title="Title",
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
            metadata={"vector_id": 1},
        )
        kb.documents[doc_id] = doc
        kb.search_index = {}

        mock_vs = MagicMock()
        mock_vs.update_document.side_effect = Exception("Vector backend down")
        mock_get_vs.return_value = mock_vs

        result = kb.update_document(doc_id, {"title": "Updated"})

        self.assertTrue(result)
        self.assertEqual(kb.documents[doc_id].title, "Updated")

    @patch("core.knowledge_base_system._get_vector_search")
    def test_kb_update_self_heals_when_vector_id_missing(self, mock_get_vs):
        """KB update with no vector_id re-adds doc to vector and stores vector_id."""
        from core.knowledge_base_system import KnowledgeBaseSystem, KnowledgeDocument
        from core.knowledge_base_system import DocumentType, ContentFormat
        from datetime import datetime

        kb = KnowledgeBaseSystem()
        doc_id = "test_selfheal_doc"
        doc = KnowledgeDocument(
            id=doc_id,
            title="Heal Me",
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
            metadata={},
        )
        kb.documents[doc_id] = doc
        kb.search_index = {}

        mock_vs = MagicMock()
        mock_vs.add_document.return_value = 777
        mock_get_vs.return_value = mock_vs

        result = kb.update_document(doc_id, {"content": "Updated content"})

        self.assertTrue(result)
        mock_vs.add_document.assert_called_once()
        self.assertEqual(doc.metadata.get("vector_id"), 777)


if __name__ == "__main__":
    unittest.main()
