#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal Vector Search Service
Lightweight vector search for RAG (Retrieval-Augmented Generation).
"""

import json
import pickle
import math
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

class MinimalVectorSearch:
    """Minimal vector search service - lightweight version."""
    
    def __init__(self, vector_db_path: str = "data/vector_db.pkl"):
        """Initialize vector search service."""
        self.vector_db_path = Path(vector_db_path)
        self.vectors = []
        self.documents = []
        self.metadata = []
        self.dimension = 384  # Default dimension for sentence-transformers
        
        # Load existing data
        self.load_vector_db()
    
    def load_vector_db(self) -> bool:
        """Load vector database from file."""
        try:
            if self.vector_db_path.exists():
                with open(self.vector_db_path, 'rb') as f:
                    data = pickle.load(f)
                    self.vectors = data.get('vectors', [])
                    self.documents = data.get('documents', [])
                    self.metadata = data.get('metadata', [])
                
                print(f"✅ Loaded {len(self.vectors)} vectors from {self.vector_db_path}")
                return True
            else:
                print(f"📝 No vector database found at {self.vector_db_path}")
                return True
        except Exception as e:
            print(f"❌ Error loading vector database: {e}")
            return False
    
    def save_vector_db(self) -> bool:
        """Save vector database to file."""
        try:
            # Ensure directory exists
            self.vector_db_path.parent.mkdir(exist_ok=True)
            
            data = {
                'vectors': self.vectors,
                'documents': self.documents,
                'metadata': self.metadata
            }
            
            with open(self.vector_db_path, 'wb') as f:
                pickle.dump(data, f)
            
            print(f"✅ Saved {len(self.vectors)} vectors to {self.vector_db_path}")
            return True
        except Exception as e:
            print(f"❌ Error saving vector database: {e}")
            return False
    
    def add_document(self, text: str, metadata: Dict[str, Any] = None) -> int:
        """Add a document to the vector database."""
        try:
            # Generate embedding
            embedding = self._generate_embedding(text)
            
            # Add to database
            doc_id = len(self.documents)
            self.vectors.append(embedding)
            self.documents.append(text)
            self.metadata.append(metadata or {})
            
            print(f"✅ Added document {doc_id} to vector database")
            return doc_id
            
        except Exception as e:
            print(f"❌ Error adding document: {e}")
            return -1
    
    def search_similar(self, query: str, top_k: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        try:
            if not self.vectors:
                print("⚠️  No vectors in database")
                return []
            
            # Generate query embedding
            query_embedding = self._generate_embedding(query)
            
            # Calculate similarities
            similarities = []
            for i, vector in enumerate(self.vectors):
                similarity = self._cosine_similarity(query_embedding, vector)
                if similarity >= threshold:
                    similarities.append({
                        'index': i,
                        'similarity': similarity,
                        'document': self.documents[i],
                        'metadata': self.metadata[i]
                    })
            
            # Sort by similarity (highest first)
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Return top k results
            results = similarities[:top_k]
            print(f"✅ Found {len(results)} similar documents")
            return results
            
        except Exception as e:
            print(f"❌ Error searching: {e}")
            return []
    
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
                
                # Add document with similarity score
                context_part = f"[Similarity: {similarity:.2f}] {doc_text}"
                
                if current_length + len(context_part) <= max_context_length:
                    context_parts.append(context_part)
                    current_length += len(context_part)
                else:
                    break
            
            context = "\n\n".join(context_parts)
            print(f"✅ Generated context ({len(context)} chars)")
            return context
            
        except Exception as e:
            print(f"❌ Error generating context: {e}")
            return "Error generating context."
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        try:
            # Use simple hash-based embedding (no heavy dependencies)
            return self._hash_embedding(text)
                
        except Exception as e:
            print(f"❌ Error generating embedding: {e}")
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
            print(f"❌ Error calculating similarity: {e}")
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
            
            print(f"✅ Added {added_count} documents to knowledge base")
            return True
            
        except Exception as e:
            print(f"❌ Error adding knowledge base: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector database statistics."""
        return {
            "total_documents": len(self.documents),
            "vector_dimension": self.dimension,
            "database_size_mb": self.vector_db_path.stat().st_size / (1024 * 1024) if self.vector_db_path.exists() else 0,
            "has_sentence_transformers": self._check_sentence_transformers()
        }
    
    def _check_sentence_transformers(self) -> bool:
        """Check if sentence-transformers is available."""
        try:
            import sentence_transformers
            return True
        except ImportError:
            return False

def create_vector_search(vector_db_path: str = "data/vector_db.pkl") -> MinimalVectorSearch:
    """Create and return a vector search instance."""
    return MinimalVectorSearch(vector_db_path)

if __name__ == "__main__":
    # Test the vector search service
    print("🧪 Testing Minimal Vector Search Service")
    print("=" * 50)
    
    vector_search = MinimalVectorSearch("data/test_vector_db.pkl")
    
    # Test adding documents
    print("Testing document addition...")
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
    
    print(f"✅ Added documents: {doc1_id}, {doc2_id}, {doc3_id}")
    
    # Test search
    print("\nTesting similarity search...")
    results = vector_search.search_similar("How can I get pricing for your services?", top_k=3)
    
    for i, result in enumerate(results):
        print(f"✅ Result {i+1}: {result['similarity']:.3f} - {result['document'][:50]}...")
    
    # Test RAG context
    print("\nTesting RAG context generation...")
    context = vector_search.get_context_for_rag("I need help with email automation")
    print(f"✅ Context generated: {context[:100]}...")
    
    # Test stats
    print("\nTesting stats...")
    stats = vector_search.get_stats()
    print(f"✅ Stats: {stats}")
    
    # Test saving
    print("\nTesting save...")
    vector_search.save_vector_db()
    
    print("\n🎉 All vector search tests completed!")
