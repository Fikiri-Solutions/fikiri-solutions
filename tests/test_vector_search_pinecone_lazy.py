#!/usr/bin/env python3
"""Regression: Pinecone network I/O is deferred until first vector operation."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("FLASK_ENV", "test")
os.environ["SKIP_HEAVY_DEP_CHECKS"] = "true"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.vector_search import MinimalVectorSearch, PineconeUnavailableError


class TestPineconeLazyInit(unittest.TestCase):
    def _mock_pinecone_sdk(self):
        mock_client = MagicMock()
        mock_index = MagicMock()
        mock_client.list_indexes.return_value = [MagicMock(name="fikiri-vectors")]
        mock_client.Index.return_value = mock_index
        mock_desc = MagicMock()
        mock_desc.dimension = 384
        mock_client.describe_index.return_value = mock_desc

        mock_pc_module = MagicMock()
        mock_pc_module.Pinecone.return_value = mock_client
        mock_pc_module.ServerlessSpec = MagicMock()
        return mock_client, mock_index, mock_pc_module

    def test_init_with_api_key_does_not_call_list_indexes(self):
        fd, path = tempfile.mkstemp(suffix=".pkl")
        os.close(fd)
        Path(path).unlink(missing_ok=True)
        mock_client, _, mock_pc_module = self._mock_pinecone_sdk()
        env = {
            "PINECONE_API_KEY": "test-key",
            "PINECONE_INDEX_NAME": "fikiri-vectors",
        }
        try:
            with patch.dict(os.environ, env, clear=False):
                with patch.dict("sys.modules", {"pinecone": mock_pc_module}):
                    vs = MinimalVectorSearch(vector_db_path=path)
            self.assertTrue(vs._pinecone_configured)
            self.assertFalse(vs._pinecone_index_ready)
            self.assertFalse(vs.use_pinecone)
            mock_client.list_indexes.assert_not_called()
        finally:
            Path(path).unlink(missing_ok=True)

    def test_first_search_calls_ensure_once(self):
        fd, path = tempfile.mkstemp(suffix=".pkl")
        os.close(fd)
        Path(path).unlink(missing_ok=True)
        mock_client, mock_index, mock_pc_module = self._mock_pinecone_sdk()
        mock_index.query.return_value = MagicMock(matches=[])
        env = {
            "PINECONE_API_KEY": "test-key",
            "PINECONE_INDEX_NAME": "fikiri-vectors",
        }
        try:
            with patch.dict(os.environ, env, clear=False):
                with patch.dict("sys.modules", {"pinecone": mock_pc_module}):
                    vs = MinimalVectorSearch(vector_db_path=path)
                    vs.search_similar("hello", top_k=1, threshold=0.0)
                    vs.search_similar("world", top_k=1, threshold=0.0)
            self.assertEqual(mock_client.list_indexes.call_count, 1)
            self.assertTrue(vs._pinecone_index_ready)
            mock_index.query.assert_called()
        finally:
            Path(path).unlink(missing_ok=True)

    def test_pinecone_unavailable_raises_on_operation(self):
        fd, path = tempfile.mkstemp(suffix=".pkl")
        os.close(fd)
        Path(path).unlink(missing_ok=True)
        env = {"PINECONE_API_KEY": "test-key"}
        try:
            with patch.dict(os.environ, env, clear=False):
                vs = MinimalVectorSearch(vector_db_path=path)
                with patch.object(
                    vs,
                    "_ensure_pinecone_index",
                    side_effect=PineconeUnavailableError("network down"),
                ):
                    with self.assertRaises(PineconeUnavailableError):
                        vs.search_similar("q", top_k=1, threshold=0.0)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_no_api_key_uses_local_without_pinecone_import(self):
        fd, path = tempfile.mkstemp(suffix=".pkl")
        os.close(fd)
        Path(path).unlink(missing_ok=True)
        env = {"PINECONE_API_KEY": ""}
        try:
            with patch.dict(os.environ, env, clear=False):
                vs = MinimalVectorSearch(vector_db_path=path)
            self.assertFalse(vs._pinecone_configured)
            results = vs.search_similar("test", top_k=1, threshold=0.0)
            self.assertEqual(results, [])
        finally:
            Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
