"""
Unit tests for core/ai/embedding_client.py.
"""

import os
import sys
from unittest.mock import patch

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai import embedding_client


class TestEmbeddingClientModule:
    def test_get_embedding_dimension_constant(self):
        dim = embedding_client.get_embedding_dimension()
        assert dim == 1536
        assert embedding_client.OPENAI_EMBEDDING_DIMENSION == 1536

    def test_openai_embedding_model_constant(self):
        assert embedding_client.OPENAI_EMBEDDING_MODEL == "text-embedding-ada-002"

    def test_get_embedding_returns_none_when_client_disabled(self):
        with patch.object(embedding_client, "_get_client", return_value=None):
            result = embedding_client.get_embedding("hello")
        assert result is None

    def test_is_embedding_available_false_when_client_disabled(self):
        with patch.object(embedding_client, "_get_client", return_value=None):
            available = embedding_client.is_embedding_available()
        assert available is False
