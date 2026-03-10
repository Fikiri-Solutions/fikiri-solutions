# FAQ / Chatbot Code Audit

Audit of all code related to the Smart FAQ and public/internal chatbot: modules, APIs, scripts, data flow, and recommendations.

---

## 1. Scope

| Area | Location | Purpose |
|------|----------|---------|
| Public chatbot API | `core/public_chatbot_api.py` | Embeddable query/feedback/eval/health (API key) |
| Smart FAQ engine | `core/smart_faq_system.py` | In-memory FAQ matching (exact, variation, keyword, semantic) |
| Chatbot internal API | `core/chatbot_smart_faq_api.py` | FAQ CRUD, KB, feedback (rating), revectorize, conversations, channels |
| Feedback system | `core/chatbot_feedback.py` | conversation_feedback + eval stats (query_log join) |
| Chatbot auth | `core/chatbot_auth.py` | require_api_key_or_jwt for KB/import/revectorize |
| Escalation | `core/expert_escalation.py` | Low-confidence → escalated_questions |
| Vector search | `core/minimal_vector_search.py` | Shared vector index (FAQ/KB) |
| Knowledge base | `core/knowledge_base_system.py` | Documents, search, tenant isolation |
| Context / multi-channel | `core/context_aware_responses.py`, `core/multi_channel_support.py` | Conversations, channel routing |
| DB schema/migrations | `core/database_optimization.py` | chatbot_query_log, conversation_feedback, chatbot_feedback |
| Eval scripts | `scripts/build_eval_sets.py`, `run_eval.py`, `dump_incorrect_for_review.py`, `weekly_rag_improve.sh` | Eval sets, metrics, incorrect dump, weekly workflow |

---

## 2. Public Chatbot API (`core/public_chatbot_api.py`)

**Blueprint:** `public_chatbot_bp`, prefix `/api/public/chatbot`.

**Endpoints:**

- **POST /query** — Main Q&A. Requires `X-API-Key` (or `Authorization: Bearer <key>`). Body: `query`, optional `conversation_id`, `context`, `lead`. Flow: tenant from API key → FAQ + KB + optional vector search (feature flag) → build sources → if no context, `fallback_needed`; else LLM with `CHATBOT_RESPONSE_SCHEMA_V1`. Combined confidence = 0.5× retrieval + 0.5× LLM; if below `CHATBOT_CONFIDENCE_THRESHOLD` (default 0.4), answer replaced with clarifying message and `fallback_used=True`. Lead capture, escalation when low confidence, then log to `chatbot_query_log` (with metadata: retrieval_confidence, llm_confidence, threshold) and return response including `confidence`, `retrieval_confidence`, `llm_confidence`, `message_id`, etc.
- **POST /feedback** — Record helpful/not + optional `feedback_text`, `message_id`, `confidence`, `metadata`. Calls `ChatbotFeedbackSystem.record_feedback`; stores in `conversation_feedback` (with optional `metadata` column).
- **GET /evaluation** — Tenant-scoped eval stats (query_log + conversation_feedback join): total_queries, fallback_rate, helpfulness_rate, avg_confidence when helpful/not.
- **GET /health** — No auth; returns status and timestamp.

**Helpers:** `_extract_lead_info`, `_record_billing_usage`, `_check_plan_access`, `_build_sources`, `_retrieval_metadata`, `_retrieval_confidence`, `_combine_confidence`, `_low_confidence_message`, `_confidence_threshold`, `_build_context_snippets`, `_safe_fallback_response`, `require_api_key`, `record_api_usage`. CORS applied in `after_request`.

**Dependencies:** api_key_manager, smart_faq, knowledge_base, context_system, LLMRouter, db_optimizer, feature_flags, expert_escalation, chatbot_feedback, enhanced_crm_service.

---

## 3. Smart FAQ System (`core/smart_faq_system.py`)

**Classes:** `FAQCategory`, `MatchConfidence`, `FAQEntry`, `FAQMatch`, `FAQResponse`, `SmartFAQSystem`.

**Data:** FAQs loaded in-memory in `_load_default_faqs()` (general, pricing, technical, features, landscaping, support). Inverted keyword index `_keyword_index` for O(1) keyword→FAQ lookups.

**Search flow:** `search_faqs(query, max_results=5)` → clean query, extract keywords → exact (≥0.9), variation (≥0.8), keyword (overlap ≥0.3), semantic (regex patterns) → dedupe by FAQ id (keep max confidence) → sort by confidence, take top `max_results` → suggested questions, fallback if no matches or best &lt; 0.4.

**CRUD:** `add_faq`, `update_faq`, `delete_faq` (in-memory only). `record_faq_usage`, `get_faq_statistics`, `export_faqs`, `import_faqs`.

**Note:** `FAQResponse` has no `.query` field. Callers that use `response.query` (e.g. `chatbot_smart_faq_api` search_faqs) correctly use `hasattr(response, 'query')` and fall back to the request `query`.

---

## 4. Chatbot Internal API (`core/chatbot_smart_faq_api.py`)

**Blueprint:** `chatbot_bp`, prefix `/api/chatbot`.

**FAQ:** POST /faq/search (query, max_results), GET /faq/categories, GET /faq/statistics, POST /faq/&lt;id&gt;/feedback, POST /faq (create; optional vector add via `get_vector_search().add_document`).

**Knowledge base:** POST /knowledge/search, GET /knowledge/document/&lt;id&gt;, POST /knowledge/documents (create + vector), POST /knowledge/import, POST /knowledge/import/bulk (require_api_key_or_jwt), POST /knowledge/revectorize (require_api_key_or_jwt; tenant-scoped), GET /knowledge/categories, GET /knowledge/popular, POST /knowledge/vectorize.

**Feedback (rating):** POST /feedback — body: question, answer, retrieved_doc_ids, rating ∈ {correct, somewhat_correct, somewhat_incorrect, incorrect}. Writes to **chatbot_feedback** (not conversation_feedback). Used for eval-set building (build_eval_sets.py).

**Conversations:** POST /conversation/start, POST /conversation/&lt;id&gt;/message, POST /conversation/&lt;id&gt;/respond, GET /conversation/&lt;id&gt;, POST /conversation/&lt;id&gt;/close.

**Channels:** GET /channels, POST /channels/&lt;type&gt;/message, POST /channels/&lt;type&gt;/test, GET /channels/statistics.

**Unified chat:** POST /chat — multi_channel.process_message(ChannelType.WEB_CHAT, …).

**Status/analytics:** GET /status, GET /analytics/comprehensive.

**Auth:** Most routes have no decorator; /knowledge/import, /import/bulk, /revectorize use `require_api_key_or_jwt`. Public widget uses **public_chatbot_api** (API key), not these internal routes.

---

## 5. Feedback and Logging

**Two feedback tables:**

- **conversation_feedback** — Used by **public** widget: conversation_id, message_id, helpful, feedback_text, user_id, metadata (optional). Populated by `ChatbotFeedbackSystem.record_feedback` (public_chatbot_api POST /feedback). Join key with chatbot_query_log: conversation_id + message_id.
- **chatbot_feedback** — Used by **internal** rating API (POST /api/chatbot/feedback): question, answer, retrieved_doc_ids, rating, metadata, prompt_version, retriever_version. Source for build_eval_sets.py (gold / needs_review / ambiguous).

**chatbot_query_log** — Each public query/response: conversation_id, message_id, query, response, confidence, fallback_used, sources_json, tenant_id, user_id, llm_trace_id, metadata (JSON: retrieval_confidence, llm_confidence, confidence_threshold). Insert tolerates missing metadata column (fallback INSERT without it).

---

## 6. Eval and Weekly Maintenance

- **build_eval_sets.py** — Reads `chatbot_feedback`, splits by rating into gold (correct), needs_review (somewhat_incorrect, incorrect), ambiguous (somewhat_correct). Writes timestamped JSONL under `data/evals/`.
- **run_eval.py** — Loads latest gold/needs_review/ambiguous JSONL, computes heuristic metrics (recall@1, recall@3, % with citations, avg answer length, correct/needs_review/ambiguous rates), writes `data/evals/report_{timestamp}.json`. MRR/groundedness/relevance left as null (would need labeled data or Ragas).
- **dump_incorrect_for_review.py** — Reads latest needs_review_*.jsonl, writes top N (default 50) to `data/evals/incorrect_for_review_{timestamp}.md` (markdown table).
- **weekly_rag_improve.sh** — (1) build_eval_sets, (2) run_eval, (3) dump_incorrect_for_review; (4) optional `--reindex` via POST /api/chatbot/knowledge/revectorize (requires API_URL and CHATBOT_API_KEY or API_KEY). Documented in CHATBOT_EVAL.md.

---

## 7. Database and Migrations

**Tables:** chatbot_query_log (with optional metadata), conversation_feedback (with optional metadata), chatbot_feedback. Migrations in `database_optimization._run_migrations()` add metadata column to chatbot_query_log and conversation_feedback if missing (PRAGMA table_info + ALTER TABLE).

---

## 8. Tests and Docs

**Tests:** test_public_chatbot_api.py, test_public_chatbot_tenant_isolation.py, test_chatbot_feedback.py, test_revenue_chatbot_flow.py (and others touching chatbot/FAQ).

**Docs:** CHATBOT_EVAL.md, CHATBOT_EMBED.md, CHATBOT_FEEDBACK_API.md, CHATBOT_KB_PIPELINE_MAP.md, CHATBOT_KB_IMPORT.md, CHATBOT_IMPLEMENTATION.md, demo/CHATBOT_GUIDE.md.

---

## 9. Findings and Recommendations

**Strengths**

- Clear split: public API (API key, query/feedback/eval) vs internal API (FAQ/KB/conversations/channels).
- Combined confidence (retrieval + LLM) and low-confidence override with configurable threshold.
- Query log and feedback metadata support eval and analytics; fallback INSERT when metadata column absent.
- Eval pipeline (build → run_eval → dump incorrect) and weekly script with optional reindex are documented.

**Issues / risks**

1. **Two feedback flows** — Public widget uses conversation_feedback (helpful/not + message_id). Internal POST /api/chatbot/feedback uses chatbot_feedback (question, answer, rating). Eval scripts use **chatbot_feedback** only. If the widget only calls public /feedback, no rows go to chatbot_feedback and build_eval_sets will have no data unless another client submits to POST /api/chatbot/feedback. Consider documenting or unifying how widget feedback is converted into chatbot_feedback (e.g. background job or dual-write) if eval sets should include widget traffic.
2. **FAQ persistence** — Smart FAQ is in-memory; restart loses runtime changes. Add/update/delete only affect process lifetime unless a persistence layer is added.
3. **create_faq_entry** — On success returns `vector_id` from a block where `vector_id` may be set only in the try; if vector add fails, the variable can be undefined in the response. Code uses `vector_id if 'vector_id' in locals() else None`; safe but slightly fragile.
4. **Revectorize auth** — weekly_rag_improve.sh --reindex calls /api/chatbot/knowledge/revectorize with X-API-Key. That route uses require_api_key_or_jwt; API key must have chatbot scope (chatbot_auth checks "chatbot:query"). Document that the key used for revectorize must have that scope.

**Recommendations**

- Add a short “Feedback and eval data” section in CHATBOT_KB_PIPELINE_MAP or CHATBOT_EVAL that states: eval sets come from **chatbot_feedback**; public widget writes to **conversation_feedback**; to use widget data for eval, either have the widget also call POST /api/chatbot/feedback with derived rating or add a sync from conversation_feedback → chatbot_feedback.
- Consider adding an integration test for the full public flow: query → log in chatbot_query_log → feedback with metadata → evaluation stats.
- Keep confidence threshold and weight (0.5/0.5) configurable (e.g. env or config) if you tune them later.

---

## 10. File List (FAQ/Chatbot)

| File | Role |
|------|------|
| core/public_chatbot_api.py | Public query, feedback, evaluation, health |
| core/smart_faq_system.py | FAQ matching and in-memory CRUD |
| core/chatbot_smart_faq_api.py | Internal FAQ/KB/conversations/channels/feedback |
| core/chatbot_feedback.py | conversation_feedback + eval stats |
| core/chatbot_auth.py | require_api_key_or_jwt |
| core/expert_escalation.py | Low-confidence escalation |
| core/database_optimization.py | Tables + migrations for query_log, feedback |
| scripts/build_eval_sets.py | chatbot_feedback → gold/needs_review/ambiguous JSONL |
| scripts/run_eval.py | Heuristic eval → report_*.json |
| scripts/dump_incorrect_for_review.py | needs_review → incorrect_for_review_*.md |
| scripts/weekly_rag_improve.sh | Weekly workflow + optional --reindex |
| docs/CHATBOT_*.md, CHATBOT_KB_PIPELINE_MAP.md | Docs and pipeline map |
