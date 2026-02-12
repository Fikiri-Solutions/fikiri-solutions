#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal Vector Search Service
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
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class MinimalVectorSearch:
    """Minimal vector search service with production enhancements."""
    
    def __init__(self, vector_db_path: str = "data/vector_db.pkl", services: Dict[str, Any] = None):
        """Initialize vector search service with enhanced features."""
        self.vector_db_path = Path(vector_db_path)
        self.services = services or {}
        self.vectors = []
        self.documents = []
        self.metadata = []
        self.dimension = 384  # Default dimension for sentence-transformers
        
        # Pinecone client (optional)
        self.pinecone_client = None
        self.pinecone_index = None
        self.use_pinecone = False
        
        # Embedding models (OpenAI only via core.ai.embedding_client)
        self.sentence_transformer = None  # Lazy-loaded instance
        self._SentenceTransformer = None  # Class reference for lazy loading
        self._use_embedding_client = False  # True when using core.ai.embedding_client for OpenAI
        self.openai_client = None  # Deprecated: do not set; use _use_embedding_client + get_embedding()
        self.embedding_model = "hash"  # hash, sentence_transformers, openai
        
        # Try Pinecone first (if configured)
        self._initialize_pinecone()
        
        # Initialize embedding models
        self._initialize_embedding_models()
        
        # Load existing data (only if not using Pinecone)
        if not self.use_pinecone:
            self.load_vector_db()
    
    def _initialize_pinecone(self):
        """Initialize Pinecone if API key is available."""
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            return
        
        try:
            from pinecone import Pinecone, ServerlessSpec
            index_name = os.getenv("PINECONE_INDEX_NAME", "fikiri-vectors")
            
            self.pinecone_client = Pinecone(api_key=api_key)
            
            # Create index if needed
            existing = [idx.name for idx in self.pinecone_client.list_indexes()]
            if index_name not in existing:
                self.pinecone_client.create_index(
                    name=index_name,
                    dimension=384,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
            
            self.pinecone_index = self.pinecone_client.Index(index_name)
            self.use_pinecone = True
            self.dimension = 384
            logger.info(f"✅ Pinecone initialized: {index_name}")
        except ImportError:
            pass  # Pinecone not installed, use local storage
        except Exception as e:
            logger.warning(f"Pinecone failed: {e}, using local storage")
    
    def _initialize_embedding_models(self):
        """Initialize available embedding models (lazy loading to avoid mutex contention)."""
        # Try sentence-transformers first (lazy load - don't initialize model until needed)
        try:
            from sentence_transformers import SentenceTransformer
            # Store class, not instance (lazy initialization)
            self._SentenceTransformer = SentenceTransformer
            self.dimension = 384  # all-MiniLM-L6-v2 dimension
            self.embedding_model = "sentence_transformers"
            logger.info("✅ Sentence-transformers available (lazy loading)")
        except ImportError:
            logger.info("ℹ️ Sentence-transformers not available")
            self._SentenceTransformer = None
        except Exception as e:
            logger.warning(f"Sentence-transformers import failed: {e}")
            self._SentenceTransformer = None
        
        # Try OpenAI embeddings via core.ai only (no direct openai.OpenAI here)
        if not self._SentenceTransformer:
            try:
                from core.ai.embedding_client import is_embedding_available, get_embedding_dimension
                if is_embedding_available():
                    self._use_embedding_client = True
                    self.dimension = get_embedding_dimension()
                    self.embedding_model = "openai"
                    logger.info("✅ OpenAI embeddings initialized (core.ai.embedding_client)")
            except ImportError:
                logger.info("ℹ️ core.ai.embedding_client not available")
            except Exception as e:
                logger.warning("OpenAI embedding client init failed: %s", e)
        
        # Fallback to hash-based embeddings
        if not self._SentenceTransformer and not self._use_embedding_client:
            logger.info("ℹ️ Using hash-based embeddings (no external models available)")
    
    def load_vector_db(self) -> bool:
        """Load vector database from file with compression support."""
        try:
            if self.vector_db_path.exists():
                # Try compressed first, then uncompressed
                try:
                    with gzip.open(self.vector_db_path, 'rb') as f:
                        data = pickle.load(f)
                except:
                    with open(self.vector_db_path, 'rb') as f:
                        data = pickle.load(f)
                
                self.vectors = data.get('vectors', [])
                self.documents = data.get('documents', [])
                self.metadata = data.get('metadata', [])
                
                # Normalize existing vectors if they're not normalized
                self._normalize_existing_vectors()
                
                logger.info(f"✅ Loaded {len(self.vectors)} vectors from {self.vector_db_path}")
                return True
            else:
                logger.info(f"📝 No vector database found at {self.vector_db_path}")
                return True
        except Exception as e:
            logger.error(f"❌ Error loading vector database: {e}")
            return False
    
    def save_vector_db(self) -> bool:
        """Save vector database to file with compression."""
        try:
            # Ensure directory exists
            self.vector_db_path.parent.mkdir(exist_ok=True)
            
            data = {
                'vectors': self.vectors,
                'documents': self.documents,
                'metadata': self.metadata,
                'embedding_model': self.embedding_model,
                'dimension': self.dimension,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            # Save with compression
            with gzip.open(self.vector_db_path, 'wb') as f:
                pickle.dump(data, f)
            
            logger.info(f"✅ Saved {len(self.vectors)} vectors to {self.vector_db_path} (compressed)")
            return True
        except Exception as e:
            logger.error(f"❌ Error saving vector database: {e}")
            return False
    
    def add_document(self, text: str, metadata: Dict[str, Any] = None) -> int:
        """Add a document to the vector database (Pinecone or local)."""
        if self.use_pinecone:
            return self._add_document_pinecone(text, metadata)
        else:
            return self._add_document_local(text, metadata)
    
    def _add_document_local(self, text: str, metadata: Dict[str, Any] = None) -> int:
        """Add a document to local vector database."""
        try:
            # Generate embedding
            embedding = self._generate_embedding(text)
            
            # Normalize embedding
            embedding = self._normalize_vector(embedding)
            
            # Add to database
            doc_id = len(self.documents)
            self.vectors.append(embedding)
            self.documents.append(text)
            
            # Enhanced metadata
            enhanced_metadata = {
                'created_at': datetime.now(timezone.utc).isoformat(),
                'embedding_model': self.embedding_model,
                'text_length': len(text),
                **(metadata or {})
            }
            self.metadata.append(enhanced_metadata)
            
            logger.info(f"✅ Added document {doc_id} to vector database")
            return doc_id
            
        except Exception as e:
            logger.error(f"❌ Error adding document: {e}")
            return -1
    
    def _add_document_pinecone(self, text: str, metadata: Dict[str, Any] = None) -> int:
        """Add a document to Pinecone."""
        import uuid
        embedding = self._normalize_vector(self._generate_embedding(text))
        doc_id = str(uuid.uuid4())
        
        enhanced_metadata = {
            'text': text,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'embedding_model': self.embedding_model,
            **(metadata or {})
        }
        
        self.pinecone_index.upsert(vectors=[(doc_id, embedding, enhanced_metadata)])
        return hash(doc_id) % (10**9)
    
    def update_document(self, doc_id: int, text: str, metadata: Dict[str, Any] = None) -> bool:
        """Update an existing document."""
        try:
            if doc_id < 0 or doc_id >= len(self.documents):
                logger.error(f"❌ Document ID {doc_id} out of range")
                return False
            
            # Generate new embedding
            embedding = self._generate_embedding(text)
            embedding = self._normalize_vector(embedding)
            
            # Update document
            self.vectors[doc_id] = embedding
            self.documents[doc_id] = text
            
            # Update metadata
            if metadata:
                self.metadata[doc_id].update(metadata)
            self.metadata[doc_id]['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"✅ Updated document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating document: {e}")
            return False
    
    def delete_document(self, doc_id: int) -> bool:
        """Delete a document from the database."""
        try:
            if doc_id < 0 or doc_id >= len(self.documents):
                logger.error(f"❌ Document ID {doc_id} out of range")
                return False
            
            # Remove document
            del self.vectors[doc_id]
            del self.documents[doc_id]
            del self.metadata[doc_id]
            
            logger.info(f"✅ Deleted document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting document: {e}")
            return False
    
    def search_similar(self, query: str, top_k: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar documents (Pinecone or local)."""
        if self.use_pinecone:
            return self._search_similar_pinecone(query, top_k, threshold)
        else:
            return self._search_similar_local(query, top_k, threshold)
    
    def _search_similar_local(self, query: str, top_k: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar documents - optimized with heap for top-k."""
        try:
            if not self.vectors:
                logger.warning("⚠️ No vectors in database")
                return []
            
            # Generate query embedding
            query_embedding = self._generate_embedding(query)
            query_embedding = self._normalize_vector(query_embedding)
            
            # Use heap to maintain top-k results efficiently (O(n log k) instead of O(n log n))
            import heapq
            heap = []  # Min-heap to keep top-k largest similarities
            
            # Calculate similarities - single pass O(n)
            for i, vector in enumerate(self.vectors):
                similarity = self._cosine_similarity(query_embedding, vector)
                if similarity >= threshold:
                    # Use negative similarity for min-heap (we want max)
                    if len(heap) < top_k:
                        heapq.heappush(heap, (similarity, i))
                    elif similarity > heap[0][0]:  # Better than worst in heap
                        heapq.heapreplace(heap, (similarity, i))
            
            # Extract results from heap and sort (O(k log k))
            results = []
            while heap:
                similarity, i = heapq.heappop(heap)
                results.append({
                    'index': i,
                    'similarity': similarity,
                    'document': self.documents[i],
                    'metadata': self.metadata[i]
                })
            
            # Sort by similarity descending (highest first)
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            logger.info(f"✅ Found {len(results)} similar documents")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error searching: {e}")
            return []
    
    def _search_similar_pinecone(self, query: str, top_k: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar documents in Pinecone."""
        query_embedding = self._normalize_vector(self._generate_embedding(query))
        results = self.pinecone_index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
        
        return [
            {
                'document': match.metadata.get('text', ''),
                'similarity': float(match.score),
                'metadata': {k: v for k, v in match.metadata.items() if k != 'text'},
                'id': match.id
            }
            for match in results.matches if match.score >= threshold
        ]
    
    async def search_similar_async(self, query: str, top_k: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Async version of search_similar for FastAPI compatibility."""
        # Run the synchronous method in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.search_similar, query, top_k, threshold)
    
    def get_context_for_rag(self, query: str, max_context_length: int = 1000) -> str:
        """Get context for RAG (Retrieval-Augmented Generation)."""
        try:
            # Search for relevant documents
            results = self.search_similar(query, top_k=3, threshold=0.6)
            
            if not results:
                return "No relevant context found."
            
            # Build context
            context_parts = []
            current_length = 0
            
            for result in results:
                doc_text = result['document']
                similarity = result['similarity']
                metadata = result['metadata']
                
                # Add document with similarity score and metadata
                context_part = f"[Similarity: {similarity:.2f}] {doc_text}"
                
                if current_length + len(context_part) <= max_context_length:
                    context_parts.append(context_part)
                    current_length += len(context_part)
                else:
                    break
            
            context = "\n\n".join(context_parts)
            logger.info(f"✅ Generated context ({len(context)} chars)")
            return context
            
        except Exception as e:
            logger.error(f"❌ Error generating context: {e}")
            return "Error generating context."
    
    async def get_context_for_rag_async(self, query: str, max_context_length: int = 1000) -> str:
        """Async version of get_context_for_rag for FastAPI compatibility."""
        # Run the synchronous method in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_context_for_rag, query, max_context_length)
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using available models."""
        try:
            if self._SentenceTransformer:
                # Use sentence-transformers (lazy load if needed)
                model = self._get_sentence_transformer()
                if model:
                    embedding = model.encode(text)
                else:
                    raise ValueError("Sentence transformer model failed to load")
                return embedding.tolist()
            elif self._use_embedding_client:
                from core.ai.embedding_client import get_embedding
                emb = get_embedding(text)
                if emb is not None:
                    return emb
                return self._hash_embedding(text)
            else:
                # Fallback to hash-based embedding
                return self._hash_embedding(text)
                
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}, using hash fallback")
            return self._hash_embedding(text)
    
    def _hash_embedding(self, text: str) -> List[float]:
        """Generate simple hash-based embedding as fallback."""
        # Simple hash-based embedding
        hash_value = hash(text)
        
        # Convert to vector of specified dimension
        embedding = []
        for i in range(self.dimension):
            # Use different hash functions for each dimension
            val = hash(f"{text}_{i}") % 1000
            embedding.append(val / 1000.0)  # Normalize to 0-1
        
        return embedding
    
    def _normalize_vector(self, vector: List[float]) -> List[float]:
        """Normalize vector to unit length for accurate cosine similarity."""
        try:
            # Calculate norm
            norm = math.sqrt(sum(x * x for x in vector))
            
            if norm == 0:
                return vector
            
            # Normalize
            return [x / norm for x in vector]
            
        except Exception as e:
            logger.warning(f"Vector normalization failed: {e}")
            return vector
    
    def _normalize_existing_vectors(self):
        """Normalize all existing vectors in the database."""
        try:
            normalized_count = 0
            for i, vector in enumerate(self.vectors):
                normalized_vector = self._normalize_vector(vector)
                if normalized_vector != vector:
                    self.vectors[i] = normalized_vector
                    normalized_count += 1
            
            if normalized_count > 0:
                logger.info(f"✅ Normalized {normalized_count} existing vectors")
                
        except Exception as e:
            logger.warning(f"Failed to normalize existing vectors: {e}")
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors (no numpy)."""
        try:
            # Calculate dot product
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            
            # Calculate norms
            norm_a = math.sqrt(sum(a * a for a in vec1))
            norm_b = math.sqrt(sum(b * b for b in vec2))
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            similarity = dot_product / (norm_a * norm_b)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"❌ Error calculating similarity: {e}")
            return 0.0
    
    def add_knowledge_base(self, knowledge_data: List[Dict[str, Any]]) -> bool:
        """Add knowledge base documents."""
        try:
            added_count = 0
            
            for item in knowledge_data:
                text = item.get('text', '')
                metadata = item.get('metadata', {})
                
                if text:
                    doc_id = self.add_document(text, metadata)
                    if doc_id >= 0:
                        added_count += 1
            
            logger.info(f"✅ Added {added_count} documents to knowledge base")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding knowledge base: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector database statistics."""
        stats = {
            "total_documents": len(self.documents),
            "vector_dimension": self.dimension,
            "embedding_model": self.embedding_model,
            "database_size_mb": self.vector_db_path.stat().st_size / (1024 * 1024) if self.vector_db_path.exists() else 0,
            "has_sentence_transformers": self._SentenceTransformer is not None,
            "has_openai": self._use_embedding_client,
            "compression_enabled": True,
            "async_support": True,
            "incremental_indexing": True
        }
        
        # Add model-specific stats
        if self._SentenceTransformer:
            stats["sentence_transformer_model"] = "all-MiniLM-L6-v2"
        if self._use_embedding_client:
            stats["openai_model"] = "text-embedding-ada-002"
        
        return stats
    
    def get_document_by_id(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID."""
        try:
            if doc_id < 0 or doc_id >= len(self.documents):
                return None
            
            return {
                'id': doc_id,
                'document': self.documents[doc_id],
                'metadata': self.metadata[doc_id],
                'vector': self.vectors[doc_id]
            }
        except Exception as e:
            logger.error(f"❌ Error getting document: {e}")
            return None
    
    def search_by_metadata(self, metadata_filter: Dict[str, Any], top_k: int = 10) -> List[Dict[str, Any]]:
        """Search documents by metadata filters."""
        try:
            results = []
            
            for i, metadata in enumerate(self.metadata):
                # Check if metadata matches filter
                match = True
                for key, value in metadata_filter.items():
                    if metadata.get(key) != value:
                        match = False
                        break
                
                if match:
                    results.append({
                        'index': i,
                        'document': self.documents[i],
                        'metadata': metadata
                    })
            
            # Return top k results
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"❌ Error searching by metadata: {e}")
            return []

def create_vector_search(vector_db_path: str = "data/vector_db.pkl", services: Dict[str, Any] = None) -> MinimalVectorSearch:
    """Create and return a vector search instance."""
    return MinimalVectorSearch(vector_db_path, services)

if __name__ == "__main__":
    # Test the vector search service
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    
    logger.info("🧪 Testing Enhanced Minimal Vector Search Service")
    logger.info("=" * 60)
    
    vector_search = MinimalVectorSearch("data/test_vector_db.pkl")
    
    # Test adding documents
    logger.info("Testing document addition...")
    doc1_id = vector_search.add_document(
        "Fikiri Solutions provides Gmail automation and lead management services.",
        {"category": "services", "type": "description"}
    )
    
    doc2_id = vector_search.add_document(
        "Our AI-powered email assistant can automatically respond to customer inquiries.",
        {"category": "features", "type": "ai_assistant"}
    )
    
    doc3_id = vector_search.add_document(
        "Contact us at info@fikirisolutions.com for pricing information.",
        {"category": "contact", "type": "pricing"}
    )
    
    logger.info(f"✅ Added documents: {doc1_id}, {doc2_id}, {doc3_id}")
    
    # Test search
    logger.info("Testing similarity search...")
    results = vector_search.search_similar("How can I get pricing for your services?", top_k=3)
    
    for i, result in enumerate(results):
        logger.info(f"✅ Result {i+1}: {result['similarity']:.3f} - {result['document'][:50]}...")
    
    # Test RAG context
    logger.info("Testing RAG context generation...")
    context = vector_search.get_context_for_rag("I need help with email automation")
    logger.info(f"✅ Context generated: {context[:100]}...")
    
    # Test incremental operations
    logger.info("Testing document update...")
    vector_search.update_document(doc1_id, "Fikiri Solutions provides advanced Gmail automation and comprehensive lead management services.", {"updated": True})
    
    # Test metadata search
    logger.info("Testing metadata search...")
    metadata_results = vector_search.search_by_metadata({"category": "services"})
    logger.info(f"✅ Found {len(metadata_results)} documents with category 'services'")
    
    # Test stats
    logger.info("Testing stats...")
    stats = vector_search.get_stats()
    logger.info(f"✅ Stats: {stats}")
    
    # Test saving
    logger.info("Testing save...")
    vector_search.save_vector_db()
    
    logger.info("🎉 All enhanced vector search tests completed!")