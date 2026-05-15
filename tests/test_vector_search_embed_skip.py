"""Local vector upsert skips re-embedding when document text is unchanged."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.vector_search import MinimalVectorSearch


class TestVectorSearchEmbedSkip(unittest.TestCase):
    def _new_local_vector_search(self, path):
        with patch.object(MinimalVectorSearch, "_initialize_pinecone"), patch.object(
            MinimalVectorSearch, "_initialize_embedding_models"
        ):
            return MinimalVectorSearch(vector_db_path=path)

    def test_upsert_local_skips_embedding_when_text_unchanged(self):
        fd, path = tempfile.mkstemp(suffix=".pkl")
        os.close(fd)
        Path(path).unlink(missing_ok=True)
        try:
            vs = self._new_local_vector_search(path)
            calls = {"n": 0}
            real_gen = vs._generate_embedding

            def counting_gen(text):
                calls["n"] += 1
                return real_gen(text)

            vs._generate_embedding = counting_gen
            self.assertTrue(vs._upsert_document_local("doc1", "hello world", {}))
            n_after_first = calls["n"]
            self.assertEqual(n_after_first, 1)
            self.assertTrue(
                vs._upsert_document_local("doc1", "hello world", {"tier": "a"})
            )
            self.assertEqual(calls["n"], n_after_first)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_update_document_skips_embedding_when_text_unchanged(self):
        fd, path = tempfile.mkstemp(suffix=".pkl")
        os.close(fd)
        Path(path).unlink(missing_ok=True)
        try:
            vs = self._new_local_vector_search(path)
            self.assertTrue(vs._upsert_document_local("d1", "first", {}))
            self.assertEqual(len(vs.documents), 1)
            calls = {"n": 0}
            real_gen = vs._generate_embedding

            def counting_gen(text):
                calls["n"] += 1
                return real_gen(text)

            vs._generate_embedding = counting_gen
            calls["n"] = 0
            self.assertTrue(vs.update_document(0, "first", {"x": 1}))
            self.assertEqual(calls["n"], 0)
            self.assertTrue(vs.update_document(0, "second", {}))
            self.assertEqual(calls["n"], 1)
        finally:
            Path(path).unlink(missing_ok=True)
