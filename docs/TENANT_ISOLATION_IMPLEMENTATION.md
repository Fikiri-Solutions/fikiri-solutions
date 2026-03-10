# Tenant Isolation Implementation Guide

**Priority**: 🔴 Critical (Security)  
**Estimated Time**: 4-6 hours  
**Risk**: Data leakage between customers without this fix

---

## Overview

Currently, vector search and KB search do not filter by `tenant_id`, which means one customer's data could leak into another customer's RAG context. This guide provides step-by-step implementation.

---

## Step 1: Vector Search Tenant Filtering

### 1.1 Update `MinimalVectorSearch.search_similar()`

**File**: `core/minimal_vector_search.py`

**Current signature:**
```python
def search_similar(self, query: str, top_k: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
```

**New signature:**
```python
def search_similar(self, query: str, top_k: int = 5, threshold: float = 0.7, 
                   tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
```

**Changes needed:**

1. **In `_search_similar_local()`:**
   ```python
   def _search_similar_local(self, query: str, top_k: int = 5, threshold: float = 0.7,
                             tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
       # ... existing code ...
       
       # Calculate similarities - single pass O(n)
       for i, vector in enumerate(self.vectors):
           # ADD: Filter by tenant_id if provided
           if tenant_id is not None:
               doc_tenant_id = self.metadata[i].get('tenant_id')
               if doc_tenant_id != tenant_id:
                   continue  # Skip documents from other tenants
           
           similarity = self._cosine_similarity(query_embedding, vector)
           # ... rest of existing code ...
   ```

2. **In `_search_similar_pinecone()`:**
   ```python
   def _search_similar_pinecone(self, query: str, top_k: int = 5, threshold: float = 0.7,
                                 tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
       # ... existing code ...
       
       # ADD: Filter by tenant_id in Pinecone query
       filter_dict = {}
       if tenant_id is not None:
           filter_dict['tenant_id'] = tenant_id
       
       query_response = self.pinecone_index.query(
           vector=query_embedding,
           top_k=top_k,
           include_metadata=True,
           filter=filter_dict if filter_dict else None
       )
       # ... rest of existing code ...
   ```

3. **Update `add_document()` to store tenant_id:**
   ```python
   def add_document(self, text: str, metadata: Dict[str, Any] = None) -> str:
       # ... existing code ...
       
       # Ensure tenant_id is in metadata if provided
       if metadata is None:
           metadata = {}
       # Don't override if already present
       # ... rest of existing code ...
   ```

### 1.2 Update `public_chatbot_api.py`

**File**: `core/public_chatbot_api.py`

**Location**: Around line 296 where vector search is called

**Change:**
```python
# Current:
vector_results = get_vector_search().search_similar(query, top_k=3, threshold=0.6)

# New:
tenant_id = g.api_key_info.get('tenant_id')
vector_results = get_vector_search().search_similar(
    query, 
    top_k=3, 
    threshold=0.6,
    tenant_id=tenant_id  # ADD: Pass tenant_id
)
```

### 1.3 Update KB → Vector Sync

**File**: `core/knowledge_base_system.py`

**Location**: In `add_document()` and `update_document()` methods

**Change:**
```python
# When syncing to vector index, ensure tenant_id is passed:
if 'vector_id' not in document.metadata:
    vector_id = get_vector_search().add_document(
        text=document.content,
        metadata={
            'tenant_id': document.metadata.get('tenant_id'),  # ADD: Pass tenant_id
            'doc_id': document.doc_id,
            'title': document.title,
            # ... other metadata ...
        }
    )
```

---

## Step 2: KB Search Tenant Filtering

### 2.1 Update `KnowledgeBaseSystem.search()`

**File**: `core/knowledge_base_system.py`

**Current signature:**
```python
def search(self, query: str, filters: Dict[str, Any] = None, limit: int = 10) -> SearchResponse:
```

**No signature change needed** (filters already exist), but update `_matches_filters()`:

**Location**: Around line 984

**Add tenant_id filter:**
```python
def _matches_filters(self, document: KnowledgeDocument, filters: Dict[str, Any]) -> bool:
    """Check if document matches search filters"""
    
    # ADD: Tenant isolation (highest priority)
    if 'tenant_id' in filters:
        doc_tenant_id = document.metadata.get('tenant_id')
        if doc_tenant_id != filters['tenant_id']:
            return False  # Reject documents from other tenants
    
    # ... existing filter checks ...
    if 'document_type' in filters:
        # ... existing code ...
```

### 2.2 Update KB Search Calls

**File**: `core/public_chatbot_api.py`

**Location**: Around line 289

**Change:**
```python
# Current:
kb_results = knowledge_base.search(query, {}, limit=3)

# New:
kb_filters = {}
if tenant_id:
    kb_filters['tenant_id'] = tenant_id
kb_results = knowledge_base.search(query, kb_filters, limit=3)
```

### 2.3 Ensure KB Documents Store tenant_id

**File**: `core/knowledge_base_system.py`

**Location**: In `add_document()` method

**Ensure tenant_id is stored:**
```python
def add_document(self, title: str, content: str, metadata: Dict[str, Any] = None) -> str:
    # ... existing code ...
    
    # Ensure tenant_id is in metadata
    if metadata is None:
        metadata = {}
    # tenant_id should come from caller (API endpoint)
    # ... rest of existing code ...
```

**File**: `core/chatbot_smart_faq_api.py`

**Location**: In KB document creation endpoints

**Change:**
```python
# When creating KB document, extract tenant_id from API key:
tenant_id = g.api_key_info.get('tenant_id') if hasattr(g, 'api_key_info') else None
user_id = g.api_key_info.get('user_id') if hasattr(g, 'api_key_info') else None

# Add to metadata:
metadata = {
    'tenant_id': tenant_id,
    'user_id': user_id,
    # ... other metadata ...
}

doc_id = knowledge_base.add_document(title, content, metadata)
```

---

## Step 3: Testing

### 3.1 Unit Tests

**File**: `tests/test_minimal_vector_search.py` (create if doesn't exist)

```python
def test_vector_search_tenant_isolation():
    """Test that vector search filters by tenant_id"""
    vs = MinimalVectorSearch()
    
    # Add documents for tenant A
    vs.add_document("Tenant A doc", metadata={'tenant_id': 'tenant_a'})
    
    # Add documents for tenant B
    vs.add_document("Tenant B doc", metadata={'tenant_id': 'tenant_b'})
    
    # Search as tenant A
    results_a = vs.search_similar("doc", tenant_id='tenant_a')
    assert all(r['metadata']['tenant_id'] == 'tenant_a' for r in results_a)
    
    # Search as tenant B
    results_b = vs.search_similar("doc", tenant_id='tenant_b')
    assert all(r['metadata']['tenant_id'] == 'tenant_b' for r in results_b)
```

**File**: `tests/test_knowledge_base_system.py` (create if doesn't exist)

```python
def test_kb_search_tenant_isolation():
    """Test that KB search filters by tenant_id"""
    kb = KnowledgeBaseSystem()
    
    # Add documents for tenant A
    kb.add_document("Tenant A KB", "content", metadata={'tenant_id': 'tenant_a'})
    
    # Add documents for tenant B
    kb.add_document("Tenant B KB", "content", metadata={'tenant_id': 'tenant_b'})
    
    # Search as tenant A
    results_a = kb.search("KB", filters={'tenant_id': 'tenant_a'})
    assert all(doc.metadata.get('tenant_id') == 'tenant_a' for doc in results_a.results)
    
    # Search as tenant B
    results_b = kb.search("KB", filters={'tenant_id': 'tenant_b'})
    assert all(doc.metadata.get('tenant_id') == 'tenant_b' for doc in results_b.results)
```

### 3.2 Integration Test

**File**: `tests/integration/test_tenant_isolation.py` (create)

```python
def test_public_chatbot_tenant_isolation(client):
    """Test that public chatbot respects tenant isolation"""
    
    # Create two API keys for different tenants
    api_key_a = create_api_key(tenant_id='tenant_a')
    api_key_b = create_api_key(tenant_id='tenant_b')
    
    # Add KB document for tenant A
    add_kb_document(tenant_id='tenant_a', title="Tenant A FAQ", content="Answer A")
    
    # Query as tenant A
    response_a = client.post('/api/public/chatbot/query',
        headers={'X-API-Key': api_key_a},
        json={'query': 'FAQ'}
    )
    assert 'Answer A' in response_a.json()['response']
    
    # Query as tenant B (should NOT see tenant A's data)
    response_b = client.post('/api/public/chatbot/query',
        headers={'X-API-Key': api_key_b},
        json={'query': 'FAQ'}
    )
    assert 'Answer A' not in response_b.json()['response']
```

---

## Step 4: Migration for Existing Data

If you have existing KB/vector data without `tenant_id`:

1. **Identify orphaned documents**: Documents without `tenant_id` in metadata
2. **Assign default tenant**: Option A: Assign to a "default" tenant, Option B: Mark for deletion
3. **Migration script**: `scripts/migrations/add_tenant_id_to_existing_data.py`

```python
def migrate_existing_data():
    """Add tenant_id to existing KB/vector documents"""
    # For KB documents: try to infer from user_id
    # For vector documents: try to infer from KB metadata
    # If cannot infer: mark for review or assign to default tenant
    pass
```

---

## Verification Checklist

- [ ] Vector search filters by `tenant_id` (in-memory)
- [ ] Vector search filters by `tenant_id` (Pinecone)
- [ ] KB search filters by `tenant_id`
- [ ] Public chatbot passes `tenant_id` to vector search
- [ ] Public chatbot passes `tenant_id` to KB search
- [ ] KB → Vector sync includes `tenant_id`
- [ ] KB document creation includes `tenant_id` from API key
- [ ] Unit tests pass
- [ ] Integration test passes
- [ ] Manual test: Create two tenants, verify isolation

---

## Rollback Plan

If issues arise:
1. Make `tenant_id` parameter optional (default `None` = no filtering)
2. Deploy with feature flag: `tenant_isolation_enabled`
3. Monitor for errors, gradually enable

---

*Last updated: Feb 2026*
