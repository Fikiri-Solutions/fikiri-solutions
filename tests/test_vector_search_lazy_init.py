#!/usr/bin/env python3
"""Regression: vector search must not import sentence_transformers at __init__."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("FLASK_ENV", "test")
os.environ["SKIP_HEAVY_DEP_CHECKS"] = "true"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.vector_search import MinimalVectorSearch, prefer_hash_embeddings_at_init


class TestVectorSearchLazyInit(unittest.TestCase):
    def test_init_does_not_import_sentence_transformers(self):
        imported: list = []
        real_import = __import__

        def tracking_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "sentence_transformers" or (
                fromlist and "sentence_transformers" in fromlist
            ):
                imported.append(name)
            return real_import(name, globals, locals, fromlist, level)

        fd, path = tempfile.mkstemp(suffix=".pkl")
        os.close(fd)
        Path(path).unlink(missing_ok=True)
        try:
            with patch("builtins.__import__", side_effect=tracking_import):
                with patch.object(MinimalVectorSearch, "_initialize_pinecone"):
                    vs = MinimalVectorSearch(vector_db_path=path)
            self.assertEqual(imported, [])
            self.assertTrue(prefer_hash_embeddings_at_init())
            self.assertEqual(vs.embedding_model, "hash")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_get_vector_search_completes_under_skip_heavy(self):
        import core.vector_search as vs_mod

        vs_mod._vector_search_singleton = None
        vs = vs_mod.get_vector_search()
        self.assertIsNotNone(vs)
        self.assertIn(
            vs.embedding_model,
            ("hash", "openai", "sentence_transformers_deferred"),
        )


if __name__ == "__main__":
    unittest.main()
