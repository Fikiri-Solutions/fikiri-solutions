#!/usr/bin/env python3
"""Regression tests for chatbot knowledge chunking and vector ingestion."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chatbot_knowledge_chunking import chunk_text, chunk_vector_id
from core.chatbot_vector_chunk_ingestion import build_chunk_metadata, ingest_kb_text_to_vector_store


class TestChatbotKnowledgeChunking(unittest.TestCase):
    def test_short_text_returns_one_chunk(self):
        text = "We are open Monday through Friday, 9am to 5pm."
        chunks = chunk_text(text, max_chars=1200, overlap_chars=150)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].chunk_index, 0)
        self.assertEqual(chunks[0].total_chunks, 1)
        self.assertEqual(chunks[0].text, text)

    def test_empty_text_returns_no_chunks(self):
        self.assertEqual(chunk_text(""), [])
        self.assertEqual(chunk_text("   "), [])

    def test_long_text_returns_multiple_overlapping_chunks(self):
        paragraph = "Sentence one. " * 80
        text = f"{paragraph}\n\n{paragraph}"
        chunks = chunk_text(text, max_chars=400, overlap_chars=50)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0].total_chunks, len(chunks))
        self.assertEqual(chunks[-1].chunk_index, len(chunks) - 1)
        if len(chunks) > 1:
            overlap = chunks[0].text[-50:]
            self.assertTrue(chunks[1].text.startswith(overlap) or overlap.strip() in chunks[1].text)

    def test_paragraph_boundaries_preserved_when_possible(self):
        text = "Alpha paragraph stays intact.\n\nBeta paragraph stays intact.\n\nGamma paragraph stays intact."
        chunks = chunk_text(text, max_chars=70, overlap_chars=0)
        self.assertGreater(len(chunks), 1)
        self.assertIn("Alpha paragraph stays intact.", chunks[0].text)
        self.assertNotIn("Gamma paragraph", chunks[0].text)

    def test_chunk_vector_id_single_chunk_uses_parent(self):
        self.assertEqual(chunk_vector_id("doc-1", 0, 1), "doc-1")

    def test_chunk_vector_id_multi_chunk_suffix(self):
        self.assertEqual(chunk_vector_id("doc-1", 2, 4), "doc-1__chunk_2")


class TestChatbotVectorChunkIngestion(unittest.TestCase):
    def test_build_chunk_metadata_includes_parent_and_indexes(self):
        from core.chatbot_knowledge_chunking import TextChunk

        chunk = TextChunk(text="chunk body", chunk_index=1, total_chunks=3)
        meta = build_chunk_metadata(
            {"type": "knowledge_base", "tenant_id": "tenant_a", "user_id": 7},
            parent_doc_id="parent-1",
            chunk=chunk,
        )
        self.assertEqual(meta["parent_doc_id"], "parent-1")
        self.assertEqual(meta["document_id"], "parent-1")
        self.assertEqual(meta["chunk_index"], 1)
        self.assertEqual(meta["total_chunks"], 3)
        self.assertEqual(meta["source_type"], "kb_document_chunk")
        self.assertEqual(meta["tenant_id"], "tenant_a")
        self.assertEqual(meta["user_id"], 7)

    def test_single_chunk_uses_add_document_once(self):
        vs = MagicMock()
        vs.add_document.return_value = 42
        vector_ids, primary = ingest_kb_text_to_vector_store(
            vs,
            text="Short KB snippet.",
            parent_doc_id="doc-short",
            base_metadata={"type": "knowledge_base", "tenant_id": "t1", "user_id": 3},
            use_pinecone=False,
        )
        self.assertEqual(vector_ids, [42])
        self.assertEqual(primary, 42)
        vs.add_document.assert_called_once()
        metadata = vs.add_document.call_args.kwargs["metadata"]
        self.assertEqual(metadata["tenant_id"], "t1")
        self.assertEqual(metadata["user_id"], 3)
        self.assertEqual(metadata["total_chunks"], 1)
        self.assertEqual(metadata.get("source_type"), "knowledge_base")

    def test_large_text_stores_chunk_metadata_on_every_vector(self):
        vs = MagicMock()
        counter = {"n": 0}

        def _add(**kwargs):
            counter["n"] += 1
            return counter["n"]

        vs.add_document.side_effect = _add
        long_text = ("Paragraph block. " * 40 + "\n\n") * 6
        vector_ids, primary = ingest_kb_text_to_vector_store(
            vs,
            text=long_text,
            parent_doc_id="doc-long",
            base_metadata={"type": "knowledge_base", "tenant_id": "t2", "user_id": 9},
            use_pinecone=False,
            max_chars=300,
            overlap_chars=40,
        )
        self.assertGreater(len(vector_ids), 1)
        self.assertEqual(primary, 1)
        for call in vs.add_document.call_args_list:
            metadata = call.kwargs["metadata"]
            self.assertEqual(metadata["parent_doc_id"], "doc-long")
            self.assertEqual(metadata["tenant_id"], "t2")
            self.assertEqual(metadata["user_id"], 9)
            self.assertEqual(metadata["source_type"], "kb_document_chunk")
            self.assertGreater(metadata["total_chunks"], 1)

    def test_pinecone_uses_upsert_per_chunk(self):
        vs = MagicMock()
        vs.upsert_document.return_value = True
        long_text = ("Line. " * 200) + "\n\n" + ("More line. " * 200)
        vector_ids, primary = ingest_kb_text_to_vector_store(
            vs,
            text=long_text,
            parent_doc_id="pine-doc",
            base_metadata={"type": "knowledge_base", "tenant_id": "t3"},
            use_pinecone=True,
            max_chars=250,
            overlap_chars=30,
        )
        self.assertGreater(vs.upsert_document.call_count, 1)
        self.assertEqual(len(vector_ids), vs.upsert_document.call_count)
        self.assertEqual(primary, "pine-doc__chunk_0")
        first_meta = vs.upsert_document.call_args_list[0][0][2]
        self.assertEqual(first_meta["chunk_index"], 0)
        self.assertEqual(first_meta["parent_doc_id"], "pine-doc")


class TestChatbotRetrievalWithChunkedVectors(unittest.TestCase):
    @patch("core.chatbot_retrieval.get_feature_flags")
    @patch("core.chatbot_retrieval.get_vector_search")
    @patch("core.chatbot_retrieval.knowledge_base")
    @patch("core.chatbot_retrieval.faq_system")
    def test_public_retrieval_works_with_chunked_vectors(
        self, mock_faq, mock_kb, mock_get_vs, mock_flags
    ):
        from core.chatbot_retrieval import retrieve_chatbot_context

        mock_flags.return_value.is_enabled.return_value = True
        mock_faq.search_faqs.return_value = MagicMock(success=True, matches=[])
        mock_kb.search.return_value = MagicMock(success=True, results=[])

        mock_vs = MagicMock()
        mock_vs.search_similar.return_value = [
            {
                "document": "Chunk two mentions refund policy details.",
                "similarity": 0.82,
                "metadata": {
                    "parent_doc_id": "doc-99",
                    "document_id": "doc-99",
                    "chunk_index": 1,
                    "total_chunks": 3,
                    "source_type": "kb_document_chunk",
                    "tenant_id": "tenant_a",
                },
                "id": "doc-99__chunk_1",
            }
        ]
        mock_get_vs.return_value = mock_vs

        result = retrieve_chatbot_context("refund policy", "tenant_a", 5)

        self.assertFalse(result.fallback_needed)
        self.assertEqual(result.source_count, 1)
        self.assertEqual(result.sources[0]["type"], "vector")
        self.assertIn("refund policy", result.sources[0]["content"])
        mock_vs.search_similar.assert_called_once_with(
            "refund policy", top_k=12, threshold=0.6, tenant_id="tenant_a"
        )


class TestVectorizeEndpointChunking(unittest.TestCase):
    @patch("core.chatbot_smart_faq_api.get_vector_search")
    def test_ingest_kb_vectors_does_not_reference_undefined_vector_search(self, mock_get_vs):
        from core.chatbot_smart_faq_api import _ingest_kb_vectors

        vs = MagicMock()
        vs.use_pinecone = False
        vs.add_document.return_value = 7
        mock_get_vs.return_value = vs

        vector_ids, primary = _ingest_kb_vectors(
            vs,
            "Short content",
            "doc-1",
            {"type": "knowledge_base", "document_id": "doc-1"},
        )
        self.assertEqual(vector_ids, [7])
        self.assertEqual(primary, 7)

    @patch("core.chatbot_smart_faq_api.get_vector_search")
    def test_vectorize_endpoint_chunks_large_content(self, mock_get_vs):
        from flask import Flask
        from core.chatbot_smart_faq_api import chatbot_bp

        vs = MagicMock()
        vs.use_pinecone = False
        counter = {"n": 99}

        def _add(**kwargs):
            counter["n"] += 1
            return counter["n"]

        vs.add_document.side_effect = _add
        mock_get_vs.return_value = vs

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(chatbot_bp)
        client = app.test_client()

        long_content = ("Policy detail sentence. " * 50 + "\n\n") * 4
        response = client.post(
            "/api/chatbot/knowledge/vectorize",
            json={"content": long_content, "metadata": {"tenant_id": "tenant_x", "user_id": 2}},
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(data["chunk_count"], 2)
        self.assertIsNotNone(data["vector_id"])
        self.assertIn("parent_doc_id", data)
        self.assertGreaterEqual(vs.add_document.call_count, 2)


if __name__ == "__main__":
    unittest.main()
