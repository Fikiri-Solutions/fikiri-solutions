# Chatbot Architecture

Canonical reference for Fikiri’s modular chatbot stack. Use this document when adding features so logic stays in domain modules—not in route files.

**Related (legacy / supplementary):** [CHATBOT_KB_PIPELINE_MAP.md](./CHATBOT_KB_PIPELINE_MAP.md) (older pipeline notes; some retrieval steps are outdated), [CHATBOT_EMBED.md](./CHATBOT_EMBED.md), [EMAIL_REPLY_GENERATION.md](./EMAIL_REPLY_GENERATION.md) (separate email path).

---

## 1. High-level flows

### Public widget (`POST /api/public/chatbot/query`)

**Route:** `core/public_chatbot_api.py`  
**Auth:** API key (`@require_api_key`), scopes, rate limits — stays in the route layer.

```
API key auth + rate limit
  → retrieve_chatbot_context()          # core/chatbot_retrieval.py
  → load_chatbot_config()               # core/chatbot_config.py
  → check_chatbot_usage_allowed()       # core/chatbot_usage_tracking.py (plan / tier / budget)
  → generate_chatbot_answer()           # core/chatbot_response_service.py
  → capture_chatbot_lead()              # core/chatbot_lead_capture.py (widget only)
  → escalation + query log + content events
  → record API / billing / AI usage     # core/chatbot_usage_tracking.py
  → JSON response (schema_version: v1)
```

**Does not expose:** `retrieval_debug` (internal only).

### Dashboard preview (`POST /api/chatbot/preview-query`)

**Route:** `core/chatbot_smart_faq_api.py`  
**Auth:** Session JWT (`get_current_user_id`) — no API key, no billing gates, no lead capture.

```
Session auth
  → retrieve_chatbot_context()
  → load_chatbot_config()
  → generate_chatbot_answer()           # allow_llm=True, no usage gates
  → preview JSON (answer, sources, confidence, …)
  → optional retrieval_debug if body.debug === true
```

**Frontend:** `frontend/src/pages/chatbotBuilderPreview.ts` → `apiClient.previewChatbotQuery()`.

### Builder / content (ingest → retrieval)

**Routes:** `core/chatbot_smart_faq_api.py` (FAQ, KB import, vectorize, revectorize), `core/knowledge_base_system.py` (document CRUD).

```
Upload / import / edit
  → KB document save (knowledge_base_system)
  → chunk_text()                        # core/chatbot_knowledge_chunking.py
  → ingest_kb_text_to_vector_store()    # core/chatbot_vector_chunk_ingestion.py
  → vector metadata (parent_doc_id, chunk_index, total_chunks, tenant_id)
  → on update/delete/revectorize: delete_kb_chunk_vectors()  # core/chatbot_vector_chunk_cleanup.py
  → retrieval reads chunked vectors via chatbot_retrieval.py
```

---

## 2. Module responsibility table

| Module | Owns | Must NOT own |
|--------|------|----------------|
| `core/public_chatbot_api.py` | API key auth, CORS, HTTP mapping, thin orchestration, `record_api_usage` wrapper | Retrieval, LLM prompts, chunking, CRM lead logic, billing rules |
| `core/chatbot_smart_faq_api.py` | Dashboard/builder routes, preview-query, KB/FAQ ingest endpoints, session auth for builder | Public widget billing, API key validation, duplicated retrieval/LLM logic |
| `core/chatbot_retrieval.py` | FAQ + KB + vector orchestration, source assembly, context string, `RetrievalResult`, `retrieval_debug` stats, retrieval structured logs | LLM calls, API auth, lead capture, billing |
| `core/chatbot_retrieval_diversity.py` | Per-parent vector chunk caps, adjacent-chunk support, fetch top-k expansion | Cross-source dedup, route logic |
| `core/chatbot_retrieval_dedup.py` | KB vs vector duplicate collapse by `parent_doc_id` / source id | Vector diversity, LLM |
| `core/chatbot_response_service.py` | Prompt build, `LLMRouter` call, schema validation, confidence combine, fallback text | Retrieval, auth, billing |
| `core/chatbot_config.py` | Load/merge/sanitize tenant chatbot config; whitelisted keys only | Raw metadata passthrough to prompts |
| `core/chatbot_lead_capture.py` | Extract email/phone, CRM create/reuse, lead activity, lead structured logs | Preview path, public auth |
| `core/chatbot_usage_tracking.py` | Plan/tier/budget gates, API/billing/AI usage recording, usage structured logs | Auth decorators, response JSON shape |
| `core/chatbot_knowledge_chunking.py` | `chunk_text()`, chunk IDs, chunk metadata shape | Vector store I/O, HTTP |
| `core/chatbot_vector_chunk_ingestion.py` | Multi-chunk upsert, single-chunk path, ingest orchestration | Route handlers, retrieval |
| `core/chatbot_vector_chunk_cleanup.py` | Delete/replace chunk vectors, metadata helpers for lifecycle | Ingest logic, search |
| `core/vector_search.py` | Vector index read/write (shared infra) | Chatbot-specific dedup/diversity (use chatbot_retrieval*) |
| `core/knowledge_base_system.py` | KB document model, keyword search, update → chunk sync entry | Public widget response assembly |

**Adjacent (not refactored in this stack but used by routes):**

- `core/chatbot_content_events.py` — content fingerprints, response-generated events
- `core/chatbot_feedback.py` — feedback persistence / evaluation stats
- `core/expert_escalation.py` — low-confidence escalation (called from public route)

---

## 3. Data boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│ Route layer (public_chatbot_api, chatbot_smart_faq_api)         │
│  HTTP, auth, correlation_id, jsonify, status codes              │
└────────────┬────────────────────────────────────────────────────┘
             │
    ┌────────┴────────┬──────────────┬──────────────┬─────────────┐
    ▼                 ▼              ▼              ▼             ▼
 Retrieval        Response/LLM    Config        Lead capture   Usage/billing
 (FAQ/KB/         (prompt +        (whitelist    (widget       (gates +
  vector +         schema)          merge)        only)         record_*)
  diversity +
  dedup)
             │
             ▼
 Vector lifecycle (chunk → ingest → cleanup → metadata on vectors)
             │
             ▼
 Shared infra: vector_search, knowledge_base_system, smart_faq, crm/service
```

**Tenant isolation:** `tenant_id` / `user_id` from API key or session must flow into KB filters, vector search, and chunk metadata. Never mix tenants in retrieval or ingest.

**Internal vs public payloads:**

| Field / concept | Public widget | Preview |
|-----------------|---------------|---------|
| `schema_version: v1` | Yes | No (preview shape) |
| `retrieval_debug` | Never | Only if `debug: true` + authenticated |
| `lead_id` | When captured | Never |
| Billing / AI usage | Recorded | Not recorded |

---

## 4. Contract rules

1. **Public response stability** — `POST /api/public/chatbot/query` must keep `schema_version: "v1"` and existing top-level keys (`response`, `sources`, `confidence`, `fallback_used`, `lead_id`, etc.). Additive fields only with explicit product approval.

2. **Preview debug** — `retrieval_debug` is allowed only on `POST /api/chatbot/preview-query` when the user is authenticated and the body includes `"debug": true`.

3. **No debug on public widget** — Do not expose `retrieval_debug`, raw prompts, or LLM traces in production public responses (non-prod may include `correlation_id` / `llm_trace_id` per existing env guard).

4. **Config → prompt safety** — Only whitelisted keys from `core/chatbot_config.py` may influence prompts. Never inject raw `users.metadata` or arbitrary JSON into LLM context.

5. **Structured logging / PII** — Events may include IDs, counts, booleans, and reason codes. Do **not** log raw queries, responses, emails, phones, or API key strings. See:
   - `chatbot.retrieval.completed` (`core/chatbot_retrieval.py`)
   - `chatbot.lead_capture.*` (`core/chatbot_lead_capture.py`)
   - `chatbot.usage.*` (`core/chatbot_usage_tracking.py`)

6. **LLM path** — All generation goes through `core/chatbot_response_service.py` → `core/ai/llm_router.py` with schema validation (`ChatbotResponseSchema`).

7. **Retrieval path** — All FAQ/KB/vector assembly goes through `retrieve_chatbot_context()`. Do not duplicate source building in routes.

---

## 5. Testing map

### Retrieval & context

| Test file | Covers |
|-----------|--------|
| `tests/test_chatbot_retrieval.py` | Basic `retrieve_chatbot_context`, tenant on vector search |
| `tests/test_chatbot_retrieval_diversity.py` | Vector chunk diversity, deterministic ordering |
| `tests/test_chatbot_retrieval_dedup.py` | Cross-source KB/vector dedup |
| `tests/test_chatbot_retrieval_observability.py` | `retrieval_debug`, structured logs, public vs preview debug |
| `tests/test_public_chatbot_tenant_isolation.py` | Tenant passed to KB/vector on public path |

### Chunking & vector lifecycle

| Test file | Covers |
|-----------|--------|
| `tests/test_chatbot_knowledge_chunking.py` | `chunk_text`, metadata, ingest integration |
| `tests/test_chatbot_vector_chunk_cleanup.py` | Chunk delete/replace, bounded IDs |
| `tests/test_kb_vector_sync.py` | KB `update_document` chunk re-ingest |

### Config

| Test file | Covers |
|-----------|--------|
| `tests/test_chatbot_config.py` | Config merge/sanitize defaults |
| `tests/test_chatbot_config_api.py` | GET/PUT `/api/chatbot/config`, public query uses saved config |

### Preview (backend + frontend)

| Test file | Covers |
|-----------|--------|
| `tests/test_chatbot_preview_query.py` | Preview auth, no lead/API usage, public unchanged |
| `frontend/src/__tests__/chatbotBuilderPreview.test.ts` | Preview helper, debug toggle wiring |
| `frontend/src/__tests__/apiClientChatbotPreview.test.ts` | `previewChatbotQuery` payload |
| `frontend/src/__tests__/ChatbotBuilder.test.tsx` | Builder preview UI, retrieval debug panel |

### Response / LLM

| Test file | Covers |
|-----------|--------|
| `tests/test_chatbot_response_service.py` | Answer generation, schema, fallback |
| `tests/test_public_chatbot_api.py` | End-to-end public query, tier/budget blocks, AI usage gating |

### Lead capture

| Test file | Covers |
|-----------|--------|
| `tests/test_chatbot_lead_capture.py` | Extract, CRM handoff, config disable, structured logs |
| `tests/test_public_chatbot_api.py` (`test_10*`) | Public `lead_id`, explicit payload, disabled config |

### Usage / billing

| Test file | Covers |
|-----------|--------|
| `tests/test_chatbot_usage_tracking.py` | Gates, record helpers, usage structured logs |
| `tests/test_revenue_chatbot_flow.py` | Revenue path: vector + LLM + schema v1 |
| `tests/test_revenue_billing_security.py` | Plan blocks chatbot |

### Feedback & content events

| Test file | Covers |
|-----------|--------|
| `tests/test_chatbot_feedback.py` | Feedback API |
| `tests/test_chatbot_content_events.py` | Content fingerprints |

---

## 6. Future roadmap (not implemented)

- **Conversation persistence** — durable thread storage beyond in-memory `context_system` for widget sessions
- **Chatbot config UI** — full builder surface for all whitelisted config keys (partial: GET/PUT config + preview debug today)
- **Phone-only lead capture** — dedupe/create by phone when email absent (today email required for CRM create)
- **Eval datasets** — golden questions + expected sources for regression
- **Semantic caching** — cache retrieval+answer by normalized query hash per tenant
- **Optional reranking** — post-retrieval reranker behind feature flag (today: diversity + dedup only, no ML rerank)
- **Analytics dashboard** — aggregate `chatbot_query_log`, retrieval_debug samples, usage events

---

## 7. Guardrails for new work

> **When adding chatbot features, do not put business logic directly into `public_chatbot_api.py` or `chatbot_smart_faq_api.py` unless it is strictly route-specific** (auth, HTTP status, request parsing, response jsonify).

**Do instead:**

| If you need… | Add or extend… |
|--------------|----------------|
| New retrieval source or ranking | `chatbot_retrieval.py` (+ diversity/dedup modules if vector-specific) |
| LLM behavior / prompt / schema | `chatbot_response_service.py` |
| Tenant tone, fallback, lead flags | `chatbot_config.py` |
| Widget lead behavior | `chatbot_lead_capture.py` |
| Plan/billing/usage | `chatbot_usage_tracking.py` |
| Chunking or vector writes | `chatbot_knowledge_chunking.py`, `chatbot_vector_chunk_ingestion.py`, `chatbot_vector_chunk_cleanup.py` |
| Builder ingest endpoint | Thin handler in `chatbot_smart_faq_api.py` calling the modules above |

**Before merging:**

1. Trace callers and tests for the module you touch (see §5).
2. Confirm public `schema_version: v1` unchanged unless explicitly versioned.
3. Confirm no PII in new structured log fields.
4. Run: `pytest tests/test_chatbot_retrieval*.py tests/test_public_chatbot_api.py tests/test_revenue_chatbot_flow.py tests/test_chatbot_lead_capture.py tests/test_chatbot_usage_tracking.py -v`

---

## Quick entry points (for Cursor / agents)

```
Public widget orchestration:  core/public_chatbot_api.py :: public_chatbot_query
Preview orchestration:          core/chatbot_smart_faq_api.py :: preview_chatbot_query
Retrieval:                      core/chatbot_retrieval.py :: retrieve_chatbot_context
Answer generation:              core/chatbot_response_service.py :: generate_chatbot_answer
Config:                         core/chatbot_config.py :: load_chatbot_config
Lead capture:                   core/chatbot_lead_capture.py :: capture_chatbot_lead
Usage gates + billing:          core/chatbot_usage_tracking.py :: check_chatbot_usage_allowed
Chunk ingest:                   core/chatbot_vector_chunk_ingestion.py :: ingest_kb_text_to_vector_store
```
