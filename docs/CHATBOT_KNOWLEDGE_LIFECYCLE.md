# Chatbot Knowledge Lifecycle

Canonical operational model for Chatbot Builder ingest → retrieval readiness.

## Lifecycle states

| State | Meaning |
|-------|---------|
| `uploaded` | File received (client-only until KB save) |
| `processed` | Text extracted (`/api/docs-forms/documents/process`) |
| `stored` | FAQ or KB row exists (memory + optional `chatbot_*_current`) |
| `chunked` | Chunking started for vector ingest |
| `vectorized` | Vectors written to local index or Pinecone |
| `indexed` | Chunks linked on KB metadata |
| `retrieval_ready` | Keyword and/or semantic paths usable for tenant |
| `failed` | Indexing failed; see `last_error`, `retryable` |
| `stale` | Content changed since last successful index (future) |

## Authoritative stores

| Layer | Role |
|-------|------|
| Postgres/SQLite `chatbot_kb_current` / `chatbot_faq_current` | Durable content (when `chatbot_content_events` table exists) |
| `chatbot_knowledge_lifecycle` | Per-artifact ops state (additive) |
| `background_jobs` (`kb_vectorize`) | Durable vectorization trace |
| In-memory FAQ/KB dicts | Serving cache (hydrated on boot) |
| Vector store | Semantic retrieval |

## APIs

- `GET /api/chatbot/knowledge/retrieval-health` — tenant-scoped readiness (session JWT)
- Existing ingest APIs unchanged; lifecycle rows updated on success/failure

## Preview / live

Both use `retrieve_chatbot_context()` + `generate_chatbot_answer()`. No preview-only retrieval.

## Module

`core/chatbot_knowledge_lifecycle.py`
