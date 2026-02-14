# 🔒 Mutex Contention Mitigation Guide

**Date:** January 2026  
**Status:** ✅ **Mitigations Applied**

---

## 🎯 **Understanding Mutex Warnings**

The `[mutex.cc] RAW: Lock blocking` message is usually from C-extension lock contention:
- SQLite (database operations)
- gRPC (network calls)
- Tokenizers (ML libraries)
- Other native Python extensions

---

## ✅ **Applied Mitigations**

### **1. SQLite WAL Mode + Busy Timeout** ✅

**Status:** Already configured in `database_optimization.py`

```python
# Every connection sets:
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=30000")
```

**Why:** WAL mode allows concurrent reads while writes happen, reducing lock contention.

---

### **2. Short Transactions** ✅

**Status:** HTTP calls outside transactions

**Implementation:**
```python
# Token refresh pattern:
# 1. Acquire lock (short transaction)
UPDATE integration_sync_state SET status = 'refreshing' WHERE status = 'idle'

# 2. COMMIT (transaction ends)

# 3. Perform HTTP call (NO DB LOCK HELD)
new_tokens = provider.refresh_access_token(refresh_token)

# 4. Update tokens (new short transaction)
_update_tokens(integration_id, new_tokens)
```

**Why:** Long-running transactions hold locks and cause contention.

---

### **3. Per-Request Connections** ✅

**Status:** Each `execute_query()` call gets a new connection

**Implementation:**
```python
@contextmanager
def get_connection(self, retries=3):
    """Get database connection with retry logic"""
    # Creates new connection each time
    conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
    # ... set PRAGMAs ...
    yield conn
    conn.close()  # Connection closed after use
```

**Why:** Avoids sharing connections across threads (which causes contention).

**Note:** SQLite with `check_same_thread=False` + WAL mode is safe for multi-threaded use when each thread gets its own connection.

---

### **4. Startup Transaction Optimization** ⚠️

**Status:** `_initialize_database()` does multiple operations in one transaction

**Current:**
```python
def _initialize_database(self):
    with self.get_connection() as conn:
        cursor = conn.cursor()
        self._create_optimized_tables(cursor)  # Many CREATE TABLE statements
        self._create_indexes(cursor)           # Many CREATE INDEX statements
        self._create_views(cursor)             # CREATE VIEW statements
        self._create_metrics_table(cursor)
        self._run_migrations(cursor)
        conn.commit()  # Single commit for all operations
```

**Recommendation:** This is acceptable for startup (runs once), but consider:
- Breaking into smaller transactions if startup is slow
- Running migrations separately from schema creation

---

### **5. ML/Embedding Library Lazy Loading** ✅

**Status:** `sentence_transformers` model loads lazily (not at initialization)

**Implementation:**
```python
# core/minimal_vector_search.py
def _initialize_embedding_models(self):
    """Initialize available embedding models (lazy loading to avoid mutex contention)."""
    try:
        from sentence_transformers import SentenceTransformer
        # Store class, not instance (lazy initialization)
        self._SentenceTransformer = SentenceTransformer
        # Model NOT loaded here - only class reference stored
    except ImportError:
        self._SentenceTransformer = None

def _get_sentence_transformer(self):
    """Lazy-load sentence transformer model (avoids mutex contention at startup)."""
    if self.sentence_transformer is None and self._SentenceTransformer:
        logger.info("Loading sentence-transformers model (lazy initialization)...")
        self.sentence_transformer = self._SentenceTransformer('all-MiniLM-L6-v2')
    return self.sentence_transformer

# Usage:
model = self._get_sentence_transformer()  # Loads only when first used
embedding = model.encode(text)
```

**Why:** Heavy native components (like transformers) should load lazily, not at initialization time. This prevents mutex contention during startup.

---

## 🔍 **Additional Checks**

### **Background Threads**

**Status:** ✅ No background threads sharing database connections

**Verification:**
- All database operations use `db_optimizer.execute_query()`
- Each call gets a new connection via `get_connection()`
- Connections are closed after use

---

### **Long-Running Operations**

**Status:** ✅ No long-running DB operations identified

**Verification:**
- Token refresh: HTTP call outside transaction ✅
- Integration connect: Short transaction ✅
- Query operations: Short transactions ✅

---

## 📋 **Best Practices Checklist**

- [x] **WAL mode enabled** - ✅ Every connection sets `PRAGMA journal_mode=WAL`
- [x] **Busy timeout set** - ✅ `PRAGMA busy_timeout=30000` (30 seconds)
- [x] **Short transactions** - ✅ HTTP calls outside transactions
- [x] **Per-request connections** - ✅ New connection per `execute_query()` call
- [x] **No shared connections** - ✅ Connections closed after use
- [x] **Lazy ML loading** - ✅ `sentence_transformers` loaded on demand
- [x] **No background thread sharing** - ✅ Each thread gets its own connection

---

## 🚨 **If Mutex Warnings Persist**

### **1. Check for Long Transactions**

```python
# Add logging to identify slow queries:
import time
start = time.time()
result = db_optimizer.execute_query(...)
duration = time.time() - start
if duration > 1.0:  # Log queries > 1 second
    logger.warning(f"Slow query: {duration:.2f}s - {query[:100]}")
```

### **2. Verify Connection Lifecycle**

```python
# Ensure connections are closed promptly:
with db_optimizer.get_connection() as conn:
    # Do work
    pass
# Connection automatically closed here
```

### **3. Check for Import-Time Initialization**

```python
# Bad (initializes at import):
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('model-name')  # ❌ Heavy init at import

# Good (lazy initialization):
def get_model():
    if not hasattr(get_model, '_model'):
        get_model._model = SentenceTransformer('model-name')
    return get_model._model
```

### **4. Monitor Thread Count**

```python
# Check if too many threads are accessing DB:
import threading
print(f"Active threads: {threading.active_count()}")
```

---

## ✅ **Current Status**

**All mitigations are in place:**
- ✅ WAL mode + busy timeout
- ✅ Short transactions
- ✅ Per-request connections
- ✅ Lazy ML loading
- ✅ No shared connections

**If mutex warnings still occur:**
1. Check application logs for slow queries
2. Verify no long-running transactions
3. Monitor thread count
4. Check for other C-extensions causing contention

---

### **6. Vector Search Lazy Loading** ✅ (Jan 2026)

**Status:** Applied in `core/chatbot_smart_faq_api.py`

**Problem:** `MinimalVectorSearch()` was instantiated at import time, triggering `sentence_transformers` (PyTorch) or Pinecone SDK imports right after "Multi-channel support system initialized", causing `[mutex.cc] RAW: Lock blocking` and app startup hang.

**Fix:** Lazy-initialize via `get_vector_search()` on first API use instead of at module load.

```python
# Before (blocking at import):
vector_search = MinimalVectorSearch()

# After (lazy on first request):
def get_vector_search() -> MinimalVectorSearch:
    global _vector_search
    if _vector_search is None:
        _vector_search = MinimalVectorSearch()
    return _vector_search
```

---

## 📚 **References**

- [SQLite WAL Mode](https://www.sqlite.org/wal.html)
- [SQLite Threading](https://www.sqlite.org/threadsafe.html)
- [Python Threading Best Practices](https://docs.python.org/3/library/threading.html)
