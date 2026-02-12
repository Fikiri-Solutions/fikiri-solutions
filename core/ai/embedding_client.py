"""
Fikiri Solutions - Embedding Client
Single point for OpenAI (or other) embeddings. No openai.OpenAI() outside core/ai.
"""

import os
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

# Default dimension for text-embedding-ada-002
OPENAI_EMBEDDING_DIMENSION = 1536
OPENAI_EMBEDDING_MODEL = "text-embedding-ada-002"


def get_embedding(text: str, api_key: Optional[str] = None) -> Optional[List[float]]:
    """
    Get embedding vector for text. Uses OPENAI_API_KEY. Returns None if disabled or error.
    """
    client = _get_client(api_key)
    if not client:
        return None
    return client.get_embedding(text)


def is_embedding_available(api_key: Optional[str] = None) -> bool:
    """Return True if embedding API is configured and usable."""
    client = _get_client(api_key)
    return client is not None and client.is_enabled()


def get_embedding_dimension(api_key: Optional[str] = None) -> int:
    """Return dimension of embeddings (1536 for OpenAI ada-002)."""
    return OPENAI_EMBEDDING_DIMENSION


_client: Optional["_EmbeddingClient"] = None


def _get_client(api_key: Optional[str] = None) -> Optional["_EmbeddingClient"]:
    global _client
    if _client is None:
        _client = _EmbeddingClient(api_key or os.getenv("OPENAI_API_KEY"))
    return _client if _client.is_enabled() else None


class _EmbeddingClient:
    """Internal client. All OpenAI embedding calls go through here."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._client = None
        self._enabled = bool(api_key)
        if self._enabled:
            try:
                import openai
                if hasattr(openai, "OpenAI"):
                    self._client = openai.OpenAI(api_key=self.api_key)
                else:
                    openai.api_key = self.api_key
                    self._client = openai
                logger.info("Embedding client initialized (OpenAI)")
            except ImportError:
                logger.warning("OpenAI not installed; embeddings disabled")
                self._enabled = False
            except Exception as e:
                logger.warning("Embedding client init failed: %s", e)
                self._enabled = False

    def is_enabled(self) -> bool:
        return self._enabled and self._client is not None

    def get_embedding(self, text: str) -> Optional[List[float]]:
        if not self.is_enabled():
            return None
        try:
            if hasattr(self._client, "embeddings"):
                response = self._client.embeddings.create(
                    input=text,
                    model=OPENAI_EMBEDDING_MODEL,
                )
                return response.data[0].embedding
            # Legacy
            response = self._client.Embedding.create(
                input=text,
                model=OPENAI_EMBEDDING_MODEL,
            )
            return response["data"][0]["embedding"]
        except Exception as e:
            logger.warning("Embedding call failed: %s", e)
            return None
