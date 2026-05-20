#!/usr/bin/env python3
"""
Fikiri Solutions - Vector Search Service (Canonical)
Lightweight vector search for RAG with production enhancements.
"""

import json
import pickle
import gzip
import math
import asyncio
import logging
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
pinecone = None


class PineconeUnavailableError(RuntimeError):
    """Raised when PINECONE_API_KEY is set but Pinecone cannot be used for an operation."""


def _env_truthy(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in ("1", "true", "yes", "on")


def prefer_hash_embeddings_at_init() -> bool:
    """
    When true, MinimalVectorSearch must not import sentence_transformers/torch at __init__.
    Used for tests, eval CLI, and SKIP_HEAVY_DEP_CHECKS paths.
    """
    if _env_truthy("SKIP_HEAVY_DEP_CHECKS"):
        return True
    if _env_truthy("FIKIRI_DISABLE_SENTENCE_TRANSFORMERS"):
        return True
    if (os.getenv("FIKIRI_VECTOR_EMBEDDINGS") or "").strip().lower() == "hash":
        return True
    return False


@dataclass
class QueryResponse:
    matches: List[Any]


@dataclass
class ScoredVector:
    id: str
    score: float
    metadata: Dict[str, Any]


class MinimalVectorSearch:
    """Minimal vector search service with production enhancements."""

    def __init__(self, vector_db_path: str = "data/vector_db.pkl", services: Dict[str, Any] = None):
        """Initialize vector search service with enhanced features."""
        self.vector_db_path = Path(vector_db_path)
        self.services = services or {}
        self.vectors = []
        self.documents = []
        self.metadata = []
        self.dimension = 384

        self.pinecone_client = None
        self.pinecone_index = None
        self.use_pinecone = False

        self.sentence_transformer = None
        self._SentenceTransformer = None
        self._sentence_transformers_import_attempted = False
        self._use_embedding_client = False
        self.openai_client = None
        self.embedding_model = "hash"
        self._pinecone_configured = False
        self._pinecone_index_ready = False
        self._pinecone_api_key: Optional[str] = None
        self._pinecone_index_name: str = "fikiri-vectors"
        self._pinecone_embedding_model_env: Optional[str] = None

        self._initialize_pinecone()
        self._configure_embedding_backend()
        if not self._pinecone_configured:
            self.load_vector_db()

    def _force_local_vector_search(self) -> bool:
        """In-memory / explicit opt-out paths must not lazy-connect to Pinecone."""
        path = str(self.vector_db_path)
        if path in (":memory:", ":mem:"):
            return True
        return _env_truthy("FIKIRI_FORCE_LOCAL_VECTOR_SEARCH")

    def _initialize_pinecone(self) -> None:
        """Parse Pinecone env only — no network I/O at construction time."""
        api_key = (os.getenv("PINECONE_API_KEY") or "").strip()
        if not api_key:
            return
        self._pinecone_api_key = api_key
        self._pinecone_index_name = os.getenv("PINECONE_INDEX_NAME", "fikiri-vectors")
        self._pinecone_embedding_model_env = os.getenv("PINECONE_EMBEDDING_MODEL")
        self._pinecone_configured = True

    def _ensure_pinecone_index(self) -> None:
        """
        Lazily connect to Pinecone, ensure index exists, and cache per instance.
        Raises PineconeUnavailableError when PINECONE_API_KEY is set but init fails.
        """
        if not self._pinecone_configured:
            return
        if self._pinecone_index_ready:
            return
        try:
            from pinecone import Pinecone, ServerlessSpec
        except ImportError as exc:
            raise PineconeUnavailableError(
                "Pinecone SDK not installed; install pinecone or unset PINECONE_API_KEY"
            ) from exc

        index_name = self._pinecone_index_name
        pinecone_model = self._pinecone_embedding_model_env
        try:
            self.pinecone_client = Pinecone(api_key=self._pinecone_api_key)
            existing_indexes = [idx.name for idx in self.pinecone_client.list_indexes()]
            if index_name not in existing_indexes:
                if pinecone_model:
                    try:
                        self.pinecone_client.create_index_for_model(
                            name=index_name,
                            cloud="aws",
                            region="us-east-1",
                            embed={"model": pinecone_model, "field_map": {"text": "text"}},
                        )
                        self.dimension = 1024 if "llama" in pinecone_model.lower() else 384
                    except Exception:
                        self.pinecone_client.create_index(
                            name=index_name,
                            dimension=384,
                            metric="cosine",
                            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                        )
                        self.dimension = 384
                else:
                    self.pinecone_client.create_index(
                        name=index_name,
                        dimension=384,
                        metric="cosine",
                        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                    )
                    self.dimension = 384
            self.pinecone_index = self.pinecone_client.Index(index_name)
            self.use_pinecone = True
            try:
                index_info = self.pinecone_client.describe_index(index_name)
                if hasattr(index_info, "dimension") and index_info.dimension:
                    self.dimension = index_info.dimension
            except Exception:
                pass
            if self.dimension:
                self.pinecone_dimension = self.dimension
            self._pinecone_index_ready = True
            logger.info("Pinecone index ready: %s", index_name)
        except PineconeUnavailableError:
            raise
        except Exception as exc:
            raise PineconeUnavailableError(
                f"Pinecone initialization failed for index '{index_name}': {exc}"
            ) from exc

    def _pinecone_active(self) -> bool:
        """True when this instance should route the current call through Pinecone."""
        if self._force_local_vector_search():
            return False
        # Unit tests inject a mock index without going through lazy connect.
        if self.use_pinecone and self.pinecone_index is not None:
            return True
        if not self._pinecone_configured:
            return False
        if not self._pinecone_index_ready:
            self._ensure_pinecone_index()
        return self.use_pinecone

    def _configure_embedding_backend(self) -> None:
        """
        Select embedding backend without importing sentence_transformers/torch.
        Heavy models load lazily on first _generate_embedding() when needed.
        """
        if self._pinecone_configured and self._pinecone_embedding_model_env:
            self._SentenceTransformer = None
            self._use_embedding_client = False
            self.embedding_model = "hash"
            return

        if prefer_hash_embeddings_at_init():
            self._SentenceTransformer = None
            self._use_embedding_client = False
            self.embedding_model = "hash"
            return

        if not self.dimension:
            self.dimension = 384
        self.embedding_model = "sentence_transformers_deferred"

        try:
            from core.ai.embedding_client import is_embedding_available, get_embedding_dimension

            if is_embedding_available():
                self._use_embedding_client = True
                self.dimension = get_embedding_dimension()
                self.embedding_model = "openai"
                if self._pinecone_configured and getattr(self, "pinecone_dimension", None) and self.dimension != self.pinecone_dimension:
                    self._use_embedding_client = False
                    self.embedding_model = "sentence_transformers_deferred"
                    self.dimension = self.pinecone_dimension
        except Exception:
            pass

    def _resolve_sentence_transformer_class(self):
        """Lazy import — avoids torch/sentence_transformers at module or __init__ time."""
        if self._SentenceTransformer is not None:
            return self._SentenceTransformer
        if prefer_hash_embeddings_at_init():
            return None
        if self._sentence_transformers_import_attempted:
            return None
        self._sentence_transformers_import_attempted = True
        try:
            from sentence_transformers import SentenceTransformer

            self._SentenceTransformer = SentenceTransformer
            if self.embedding_model == "sentence_transformers_deferred":
                self.embedding_model = "sentence_transformers"
            return SentenceTransformer
        except Exception as exc:
            logger.warning(
                "sentence_transformers unavailable; using hash embeddings: %s",
                exc,
            )
            self._SentenceTransformer = None
            if self.embedding_model == "sentence_transformers_deferred":
                self.embedding_model = "hash"
            return None

    def load_vector_db(self) -> bool:
        try:
            if self.vector_db_path.exists():
                try:
                    with gzip.open(self.vector_db_path, 'rb') as f:
                        data = pickle.load(f)
                except Exception:
                    with open(self.vector_db_path, 'rb') as f:
                        data = pickle.load(f)
                self.vectors = data.get('vectors', [])
                self.documents = data.get('documents', [])
                self.metadata = data.get('metadata', [])
                self._normalize_existing_vectors()
            return True
        except Exception as e:
            logger.error("Error loading vector database: %s", e)
            return False

    def save_vector_db(self) -> bool:
        try:
            self.vector_db_path.parent.mkdir(exist_ok=True)
            data = {
                'vectors': self.vectors,
                'documents': self.documents,
                'metadata': self.metadata,
                'embedding_model': self.embedding_model,
                'dimension': self.dimension,
                'last_updated': datetime.now(timezone.utc).isoformat(),
            }
            with gzip.open(self.vector_db_path, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            logger.error("Error saving vector database: %s", e)
            return False

    def add_document(self, text: Optional[str] = None, metadata: Dict[str, Any] = None, content: Optional[str] = None) -> int:
        doc_text = text if text is not None else content
        if doc_text is None:
            raise ValueError("text/content is required")
        if self._pinecone_active():
            return self._add_document_pinecone(doc_text, metadata)
        return self._add_document_local(doc_text, metadata)

    def _add_document_local(self, text: str, metadata: Dict[str, Any] = None) -> int:
        try:
            embedding = self._normalize_vector(self._generate_embedding(text))
            doc_id = len(self.documents)
            self.vectors.append(embedding)
            self.documents.append(text)
            self.metadata.append({
                'created_at': datetime.now(timezone.utc).isoformat(),
                'embedding_model': self.embedding_model,
                'text_length': len(text),
                **(metadata or {}),
            })
            return doc_id
        except Exception as e:
            logger.error("Error adding document: %s", e)
            return -1

    def _add_document_pinecone(self, text: str, metadata: Dict[str, Any] = None) -> int:
        import uuid
        embedding = self._normalize_vector(self._generate_embedding(text))
        doc_id = str(uuid.uuid4())
        enhanced_metadata = {
            'text': text,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'embedding_model': self.embedding_model,
            **(metadata or {}),
        }
        self.pinecone_index.upsert(vectors=[(doc_id, embedding, enhanced_metadata)])
        return hash(doc_id) % (10**9)

    def upsert_document(self, vector_id: str, text: str, metadata: Dict[str, Any] = None) -> bool:
        if self._pinecone_active():
            return self._upsert_document_pinecone(vector_id, text, metadata)
        return self._upsert_document_local(vector_id, text, metadata)

    def _upsert_document_pinecone(self, vector_id: str, text: str, metadata: Dict[str, Any] = None) -> bool:
        try:
            embedding = self._normalize_vector(self._generate_embedding(text))
            enhanced_metadata = {
                'text': text,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'embedding_model': self.embedding_model,
                **(metadata or {}),
            }
            self.pinecone_index.upsert(vectors=[(vector_id, embedding, enhanced_metadata)])
            return True
        except Exception as e:
            logger.error("Pinecone upsert failed: %s", e)
            return False

    def _upsert_document_local(self, vector_id: str, text: str, metadata: Dict[str, Any] = None) -> bool:
        try:
            for i, meta in enumerate(self.metadata):
                if isinstance(meta, dict) and meta.get('document_id') == vector_id:
                    if self.documents[i] == text:
                        self.metadata[i].update(metadata or {})
                        self.metadata[i]['updated_at'] = datetime.now(timezone.utc).isoformat()
                        return True
                    embedding = self._normalize_vector(self._generate_embedding(text))
                    self.vectors[i] = embedding
                    self.documents[i] = text
                    self.metadata[i].update(metadata or {})
                    self.metadata[i]['updated_at'] = datetime.now(timezone.utc).isoformat()
                    return True
            embedding = self._normalize_vector(self._generate_embedding(text))
            self.vectors.append(embedding)
            self.documents.append(text)
            self.metadata.append({
                'created_at': datetime.now(timezone.utc).isoformat(),
                'embedding_model': self.embedding_model,
                'document_id': vector_id,
                **(metadata or {}),
            })
            return True
        except Exception as e:
            logger.error("Local upsert failed: %s", e)
            return False

    def update_document(self, doc_id: int, text: str, metadata: Dict[str, Any] = None) -> bool:
        try:
            if doc_id < 0 or doc_id >= len(self.documents):
                return False
            if self.documents[doc_id] == text:
                if metadata:
                    self.metadata[doc_id].update(metadata)
                self.metadata[doc_id]['updated_at'] = datetime.now(timezone.utc).isoformat()
                return True
            embedding = self._normalize_vector(self._generate_embedding(text))
            self.vectors[doc_id] = embedding
            self.documents[doc_id] = text
            if metadata:
                self.metadata[doc_id].update(metadata)
            self.metadata[doc_id]['updated_at'] = datetime.now(timezone.utc).isoformat()
            return True
        except Exception:
            return False

    def delete_document(self, doc_id: int) -> bool:
        try:
            if doc_id < 0 or doc_id >= len(self.documents):
                return False
            del self.vectors[doc_id]
            del self.documents[doc_id]
            del self.metadata[doc_id]
            return True
        except Exception:
            return False

    def delete_document_by_id(self, vector_id: str) -> bool:
        if self._pinecone_active():
            try:
                self.pinecone_index.delete(ids=[vector_id])
                return True
            except Exception:
                return False
        try:
            for i, meta in enumerate(self.metadata):
                if isinstance(meta, dict) and meta.get("document_id") == vector_id:
                    del self.vectors[i]
                    del self.documents[i]
                    del self.metadata[i]
                    return True
            return False
        except Exception:
            return False

    def search_similar(self, query: str, top_k: int = 5, threshold: float = 0.7, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if self._pinecone_active():
            return self._search_similar_pinecone(query, top_k, threshold, tenant_id)
        return self._search_similar_local(query, top_k, threshold, tenant_id)

    def _search_similar_local(self, query: str, top_k: int = 5, threshold: float = 0.7, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            if not self.vectors:
                return []
            query_embedding = self._normalize_vector(self._generate_embedding(query))
            import heapq
            heap = []
            for i, vector in enumerate(self.vectors):
                if tenant_id is not None:
                    meta = self.metadata[i] if i < len(self.metadata) else None
                    doc_tenant_id = meta.get("tenant_id") if isinstance(meta, dict) else None
                    if doc_tenant_id != tenant_id:
                        continue
                similarity = self._cosine_similarity(query_embedding, vector)
                if similarity >= threshold:
                    if len(heap) < top_k:
                        heapq.heappush(heap, (similarity, i))
                    elif similarity > heap[0][0]:
                        heapq.heapreplace(heap, (similarity, i))
            results = []
            while heap:
                similarity, i = heapq.heappop(heap)
                results.append({
                    'index': i,
                    'similarity': similarity,
                    'document': self.documents[i],
                    'metadata': self.metadata[i],
                })
            results.sort(key=lambda x: x['similarity'], reverse=True)
            return results
        except Exception:
            return []

    def _search_similar_pinecone(self, query: str, top_k: int = 5, threshold: float = 0.7, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query_embedding = self._normalize_vector(self._generate_embedding(query))
        filter_dict = {'tenant_id': tenant_id} if tenant_id is not None else None
        results = self.pinecone_index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict,
        )
        return [
            {
                'document': match.metadata.get('text', ''),
                'similarity': float(match.score),
                'metadata': {k: v for k, v in match.metadata.items() if k != 'text'},
                'id': match.id,
            }
            for match in results.matches if match.score >= threshold
        ]

    async def search_similar_async(self, query: str, top_k: int = 5, threshold: float = 0.7, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self.search_similar, query, top_k, threshold, tenant_id)

    def get_context_for_rag(self, query: str, max_context_length: int = 1000, tenant_id: Optional[str] = None) -> str:
        try:
            results = self.search_similar(query, top_k=3, threshold=0.6, tenant_id=tenant_id)
            if not results:
                return "No relevant context found."
            try:
                cap = max(1, int(max_context_length))
            except (TypeError, ValueError):
                cap = 1000
            n = max(1, len(results))
            overhead = 48
            per_doc_budget = max(32, (cap - overhead) // n)
            context_parts = []
            current_length = 0
            for result in results:
                doc = result.get("document") or ""
                if len(doc) > per_doc_budget:
                    doc = doc[: max(0, per_doc_budget - 14)] + " [truncated]"
                sim = float(result.get("similarity") or 0.0)
                context_part = f"[Similarity: {sim:.2f}] {doc}"
                if current_length + len(context_part) + 2 <= cap:
                    context_parts.append(context_part)
                    current_length += len(context_part) + 2
                else:
                    break
            if context_parts:
                return "\n\n".join(context_parts)
            r0 = results[0]
            doc0 = (r0.get("document") or "")[: max(0, cap - 32)]
            sim0 = float(r0.get("similarity") or 0.0)
            return f"[Similarity: {sim0:.2f}] {doc0}"
        except Exception:
            return "Error generating context."

    async def get_context_for_rag_async(
        self, query: str, max_context_length: int = 1000, tenant_id: Optional[str] = None
    ) -> str:
        return await asyncio.to_thread(
            self.get_context_for_rag, query, max_context_length, tenant_id
        )

    def _get_sentence_transformer(self):
        st_class = self._resolve_sentence_transformer_class()
        if self.sentence_transformer is None and st_class:
            try:
                self.sentence_transformer = st_class("all-MiniLM-L6-v2")
            except Exception as exc:
                logger.warning("SentenceTransformer model load failed: %s", exc)
                self.sentence_transformer = None
        return self.sentence_transformer

    def _generate_embedding(self, text: str) -> List[float]:
        try:
            if self.embedding_model in (
                "sentence_transformers",
                "sentence_transformers_deferred",
            ):
                model = self._get_sentence_transformer()
                if model:
                    return model.encode(text).tolist()
                raise ValueError("Sentence transformer model failed to load")
            if self._use_embedding_client:
                from core.ai.embedding_client import get_embedding
                emb = get_embedding(text)
                if emb is not None:
                    return emb
                return self._hash_embedding(text)
            return self._hash_embedding(text)
        except Exception:
            return self._hash_embedding(text)

    def _hash_embedding(self, text: str) -> List[float]:
        return [hash(f"{text}_{i}") % 1000 / 1000.0 for i in range(self.dimension)]

    def _normalize_vector(self, vector: List[float]) -> List[float]:
        try:
            norm = math.sqrt(sum(x * x for x in vector))
            if norm == 0:
                return vector
            return [x / norm for x in vector]
        except Exception:
            return vector

    def _normalize_existing_vectors(self):
        try:
            for i, vector in enumerate(self.vectors):
                self.vectors[i] = self._normalize_vector(vector)
        except Exception:
            pass

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        try:
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            norm_a = math.sqrt(sum(a * a for a in vec1))
            norm_b = math.sqrt(sum(b * b for b in vec2))
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return float(dot_product / (norm_a * norm_b))
        except Exception:
            return 0.0

    def add_knowledge_base(self, knowledge_data: List[Dict[str, Any]]) -> bool:
        try:
            for item in knowledge_data:
                text = item.get('text', '')
                metadata = item.get('metadata', {})
                if text:
                    self.add_document(text, metadata)
            return True
        except Exception:
            return False

    def get_stats(self) -> Dict[str, Any]:
        stats = {
            "total_documents": len(self.documents),
            "vector_dimension": self.dimension,
            "embedding_model": self.embedding_model,
            "database_size_mb": self.vector_db_path.stat().st_size / (1024 * 1024) if self.vector_db_path.exists() else 0,
            "has_sentence_transformers": self._SentenceTransformer is not None,
            "has_openai": self._use_embedding_client,
            "compression_enabled": True,
            "async_support": True,
            "incremental_indexing": True,
        }
        if self._SentenceTransformer:
            stats["sentence_transformer_model"] = "all-MiniLM-L6-v2"
        if self._use_embedding_client:
            stats["openai_model"] = "text-embedding-ada-002"
        return stats

    def get_document_by_id(self, doc_id: int) -> Optional[Dict[str, Any]]:
        try:
            if doc_id < 0 or doc_id >= len(self.documents):
                return None
            return {
                'id': doc_id,
                'document': self.documents[doc_id],
                'metadata': self.metadata[doc_id],
                'vector': self.vectors[doc_id],
            }
        except Exception:
            return None

    def search_by_metadata(self, metadata_filter: Dict[str, Any], top_k: int = 10) -> List[Dict[str, Any]]:
        try:
            results = []
            for i, metadata in enumerate(self.metadata):
                if all(metadata.get(key) == value for key, value in metadata_filter.items()):
                    results.append({'index': i, 'document': self.documents[i], 'metadata': metadata})
            return results[:top_k]
        except Exception:
            return []


def create_vector_search(vector_db_path: str = "data/vector_db.pkl", services: Dict[str, Any] = None) -> MinimalVectorSearch:
    return MinimalVectorSearch(vector_db_path, services)


_vector_search_singleton: Optional[MinimalVectorSearch] = None


def get_vector_search() -> MinimalVectorSearch:
    global _vector_search_singleton
    if _vector_search_singleton is None:
        _vector_search_singleton = MinimalVectorSearch()
        logger.info("Vector search singleton initialized (first use)")
    return _vector_search_singleton

