# Knowledge Base / FAQ / Chatbot Pipeline Map

## 1. Ingestion path (where docs are stored, indexed)

| Source | Where stored | Where indexed | APIs / entry points |
|--------|--------------|---------------|---------------------|
| **FAQ** | In-memory `SmartFAQSystem.faq_entries` (dict) | Optional: vector index via `add_document` when FAQ is added via API | `POST /api/chatbot/faq` (chatbot_smart_faq_api) → `faq_system.add_faq()`; routes/expert_api also adds FAQs |
| **Knowledge base** | In-memory `KnowledgeBaseSystem.documents` (dict) | Vector store (Pinecone or local) + in-memory search index | `POST /api/chatbot/knowledge/import`, `POST /api/chatbot/knowledge/import/bulk` → `knowledge_base.add_document()` + `get_vector_search().upsert_document(doc_id, content, metadata)` |
| **Vector store** | Pinecone (cloud) or `data/vector_db.pkl` (local) | Same (vectors + metadata) | Writes happen from import paths and from KB/FAQ sync in knowledge_base_system (update_document/self-heal) |

- **No dedicated DB tables** for FAQ or KB document content; both are in-memory (process lifetime). Only the **vector store** persists across restarts (Pinecone or file).
- **Tenant isolation**: `tenant_id` / `user_id` from API key (or JWT) are passed into KB metadata and vector metadata; search filters by `tenant_id`.

---

## 2. Query path (user question → retrieval → answer)

| Step | Component | What happens |
|------|-----------|--------------|
| 1 | **Entry** | `POST /api/public/chatbot/query` (public_chatbot_api) with `X-API-Key`; body: `query`, `conversation_id`, `context`, `lead`. |
| 2 | **Auth** | `@require_api_key` → validate key, scopes (`chatbot:query`), rate limit; set `g.api_key_info` (tenant_id, user_id). |
| 3 | **Retrieval** | FAQ: `faq_system.search_faqs(query, max_results=3)`. KB: `knowledge_base.search(query, filters, limit=3)`. Vector (if feature flag `vector_search`): `get_vector_search().search_similar(query, top_k=3, threshold=0.6, tenant_id=tenant_id)`. |
| 4 | **Context** | `_build_sources()` + `_build_context_snippets(sources)` → single string for LLM. If no snippets, `fallback_needed = True`. |
| 5 | **Answer** | If plan allows LLM and not fallback_needed: `LLMRouter().process(prompt, intent="chatbot_response", output_schema=CHATBOT_RESPONSE_SCHEMA_V1)` → parse JSON for `answer`, `confidence` (LLM self-check), `fallback_used`, `sources`, `follow_up`. Else: `_safe_fallback_response()`, llm confidence 0.2. |
| 5b | **Confidence** | Combine retriever similarity (avg top-k from FAQ/KB/vector) and LLM confidence: `confidence = 0.5 * retrieval_confidence + 0.5 * llm_confidence`. If `confidence < CHATBOT_CONFIDENCE_THRESHOLD` (default 0.4), response is replaced with a clarifying / "I may be missing context" message and `fallback_used = True`. |
| 6 | **Lead / escalation** | Optional lead capture (email/phone from query or `lead` payload) → `leads` / `lead_activities`. If low confidence/fallback: `escalation_engine.escalate_question(...)` → `escalated_questions`. |
| 7 | **Response** | JSON: `query`, `response`, `sources`, `confidence`, `retrieval_confidence`, `llm_confidence`, `conversation_id`, `message_id`, `tenant_id`, `fallback_used`, `llm_trace_id`, `lead_id`, `escalated`, etc. |

- **Internal chat** (dashboard): `POST /api/chatbot/chat` → `multi_channel.process_message()` → FAQ, KB, context-aware systems → unified response (different path, same underlying FAQ/KB/vector systems).

---

## 3. APIs and DB tables used

**APIs**

- **Public (widget / embed)**  
  - `POST /api/public/chatbot/query` — main Q&A (API key).  
  - `POST /api/public/chatbot/feedback` — submit helpful/not + optional text (API key).  
  - `GET /api/public/chatbot/health` — no auth.
- **Internal (dashboard, authenticated)**  
  - `POST /api/chatbot/faq` — add FAQ.  
  - `POST /api/chatbot/faq/search` — search FAQs.  
  - `GET /api/chatbot/faq/categories`, `/faq/statistics`.  
  - `POST /api/chatbot/knowledge/import`, `POST /api/chatbot/knowledge/import/bulk` — KB import (API key or JWT).  
  - `POST /api/chatbot/knowledge/revectorize` — re-index KB into vector store.  
  - `GET /api/chatbot/knowledge/categories`, `/knowledge/search`, etc.  
  - `POST /api/chatbot/chat` — unified chat (multi-channel).

**DB tables (relevant)**

- `api_keys`, `api_key_usage` — public API auth and usage.
- `chatbot_query_log` — each turn: `conversation_id`, `message_id`, `query`, `response`, `confidence`, `fallback_used`, `sources_json`, `metadata` (JSON: `retrieval_confidence`, `llm_confidence`, `confidence_threshold`), `tenant_id`, `user_id`, `llm_trace_id`, `created_at`.
- `conversation_feedback` — feedback per message: `conversation_id`, `message_id`, `helpful`, `feedback_text`, `user_id`, `metadata` (optional JSON, e.g. `confidence_score`), `created_at`.
- `leads`, `lead_activities` — lead capture from chatbot.
- `escalated_questions`, `expert_responses` — escalation path.
- `billing_usage`, `subscriptions` — plan/usage for LLM access.

---

## 4. How the frontend calls the chatbot

- **Embed / widget**: `integrations/universal/fikiri-sdk.js` — `ChatbotFeature.query(text)` → `POST /api/public/chatbot/query` with `query`, `conversation_id`, `context`, `lead`. API key set at init (`Fikiri.init({ apiKey, apiUrl, features: ['chatbot', ...] })`). Demo: `demo/chatbot-widget.html`, `demo/chatbot-demo.html` use SDK or similar fetch to same URL.
- **Dashboard**: `frontend/src/pages/ChatbotBuilder.tsx` — uses `apiClient` for `/chatbot/faq`, `/chatbot/knowledge/documents`, `/chatbot/knowledge/vectorize`, `/chatbot/knowledge/search`, `/chatbot/faq/statistics`, `/chatbot/faq/categories` (authenticated session). The unified chat in the app uses `/api/chatbot/chat` (multi-channel), not the public `/query` endpoint.

---

## 5. Minimal code changes for feedback logging and evaluation

### Current gap

- **Feedback** is stored in `conversation_feedback` (conversation_id, message_id, helpful, feedback_text, user_id).
- **No persistent log** of the query, response, confidence, sources, or fallback_used for each turn, so you cannot:
  - Join feedback to the exact message (query/response pair).
  - Compute evaluation metrics (e.g. confidence vs. helpfulness, fallback rate, source usage).

### Minimal changes

1. **Add a query/response log table**  
   - Example: `chatbot_query_log` with columns: `id`, `conversation_id`, `message_id` (UUID per turn), `query`, `response`, `confidence`, `fallback_used`, `sources_json` (JSON), `tenant_id`, `user_id`, `llm_trace_id`, `created_at`.  
   - Create in `core/database_optimization.py` (or a small migration) with `CREATE TABLE IF NOT EXISTS chatbot_query_log (...)`.

2. **Log each turn in the public query handler**  
   - In `core/public_chatbot_api.py` in `public_chatbot_query()`:  
     - After building `answer`, `confidence`, `fallback_used`, `sources`:  
       - Generate `message_id = str(uuid.uuid4())`.  
       - Insert one row into `chatbot_query_log` (query, response, confidence, fallback_used, sources as JSON, conversation_id, message_id, tenant_id, user_id, llm_trace_id).  
     - Include `message_id` in the JSON response so the widget can send it back with feedback.

3. **Link feedback to the logged message**  
   - `POST /api/public/chatbot/feedback` already accepts `message_id`. Ensure the widget/SDK sends the `message_id` returned from the last `/query` when the user marks helpful/not. No backend change required if `conversation_feedback.message_id` is that same id; then you can join `conversation_feedback` to `chatbot_query_log` on `conversation_id` + `message_id` for evaluation.

4. **Evaluation (minimal)**  
   - **Option A (read-only analytics)**: Add an endpoint (e.g. under a dashboard or internal API) that:  
     - Selects from `chatbot_query_log` joined with `conversation_feedback` (on conversation_id + message_id).  
     - Aggregates: count, helpfulness_rate, avg(confidence) where helpful=1 vs 0, fallback_used rate, optionally by tenant_id or time bucket.  
   - **Option B (no new endpoint)**: Add a method on `ChatbotFeedbackSystem` (e.g. `get_evaluation_stats(tenant_id=None, since=None)`) that runs the same join/aggregates and returns a small dict; expose via existing expert/monitoring route if one exists.

5. **Optional: SDK / widget**  
   - In `fikiri-sdk.js`: when the user clicks thumbs up/down, call `POST /api/public/chatbot/feedback` with `conversation_id`, `message_id` (from last query response), and `helpful`. No change to backend beyond returning `message_id` from `/query`.

**Summary**

- **Backend**: (1) Create `chatbot_query_log` table. (2) In `public_chatbot_query()`, generate `message_id`, insert log row, return `message_id`. (3) Optional: evaluation stats method or endpoint that joins `chatbot_query_log` + `conversation_feedback`.  
- **Frontend/SDK**: Optional: pass `message_id` from query response into feedback request so evaluations can join query/response to feedback.
