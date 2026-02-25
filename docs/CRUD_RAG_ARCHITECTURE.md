# CRUD & RAG Architecture — Production Reference

Single source of truth for data lifecycles, RAG flow, contract surfaces, and gating. Use for audits, onboarding, and debugging.

---

## 1. CRUD Summary

### CRM (Leads/Contacts)
- **Source:** `crm/service.py` (canonical), `routes/business.py` (HTTP).
- **Create:** `create_lead()` — insert lead; **identity/dedupe:** see [§2](#2-identity--merge-policy) below.
- **Read:** `get_leads_summary()`, `get_lead_activities()`, `get_lead_pipeline()` — list/filter/paginate.
- **Update:** `update_lead()`, `update_lead_stage()` (completion API); merge-by-email on create.
- **Delete:** ✅ `delete_contact(contact_id, user_id)` — removes lead and related activities. **Deletion policy:** see [§3](#3-deletion--privacy-leadcontact-level) below.

### Knowledge Base
- **Source:** `core/knowledge_base_system.py`.
- **Create:** `add_document()`.
- **Read:** `get_document()`, `get_popular_documents()`, `get_recent_documents()`, `search()`.
- **Update:** `update_document(doc_id, updates)`.
- **Delete:** `delete_document(doc_id)`.

### Vector Index (RAG retrieval)
- **Source:** `core/minimal_vector_search.py`.
- **Create:** `add_document(text, metadata)` — embed and store (in-memory/Pinecone). **Note:** Parameter name is `text`, not `content`.
- **Read:** `search_similar(query, top_k, threshold, tenant_id=None)` — `tenant_id` parameter filters results for multi-tenant isolation.
- **Update:** `update_document(doc_id, text, metadata)`.
- **Delete:** `delete_document(doc_id)`.

### Other
- **API keys:** `core/api_key_manager.py` — create/read/revoke.
- **Billing:** `core/billing_api.py` + Stripe — subscriptions, payment methods.
- **OAuth:** `core/oauth_token_manager.py` — store/retrieve/refresh tokens.

---

## 2. Identity & Merge Policy (CRM)

- **Identity key:** Email is the canonical dedupe key for leads (phone secondary if used).
- **Behavior:** `create_lead` upserts/merges by email (no duplicate leads per user per email).
- **Implications:** Scoring, follow-ups, and mailbox automation link to the same lead by email.

---

## 3. Deletion & Privacy (Lead/Contact Level)

- **Lead-level delete:** ✅ **IMPLEMENTED**: `delete_contact(contact_id, user_id)` in `crm/service.py` and `DELETE /api/crm/contacts/<id>` endpoint. Hard delete (removes lead and related activities via CASCADE). Soft-delete option available in method signature but not yet implemented (requires `deleted_at` column).
- **User-level delete:** Soft-delete / anonymize / DSAR-style “delete my data” is handled by **`core/privacy_manager.py`**:
  - `delete_user_data(user_id)` — full user deletion (leads, activities, user row); used for GDPR-style requests.
  - Retention-based cleanup and consent logging also live here.
- **Answer for "can I delete a contact?":** ✅ **YES**: Per-contact delete via `enhanced_crm_service.delete_contact(contact_id, user_id)` or `DELETE /api/crm/contacts/<id>`. Full account deletion remains via `privacy_manager.delete_user_data()`.

---

## 4. RAG Flow

- **Orchestrator:** **`core/public_chatbot_api.py`** is the RAG orchestrator for the public chatbot. It builds context and calls the LLM once per query.
- **Helper:** `core/minimal_vector_search.get_context_for_rag()` is a **helper** used by other systems (e.g. internal tools); the public chatbot does **not** use it. It builds a single context string from vector search only.
- **Public chatbot flow:**
  1. **Extract tenant_id:** From API key (`g.api_key_info.get('tenant_id')`) for multi-tenant isolation.
  2. **Retrieve:** FAQ search (`faq_system.search_faqs`) + KB search (`knowledge_base.search` with `filters={'tenant_id': tenant_id}`) + optional vector search (`get_vector_search().search_similar(..., tenant_id=tenant_id)`) when `vector_search` flag is on.
  3. **Build context:** Combine into `context_snippets` (no separate `get_context_for_rag` call).
  4. **Generate:** Single `LLMRouter().process(...)` call with "use ONLY the provided context" and JSON schema validation.

---

## 5. RAG Safety & Limitations

- **Policy:** If context is insufficient, the bot must respond with “I don’t have enough information” (or equivalent), ask a clarifying question, or offer contact/escalation — not invent details.
- **Implementation:** The orchestrator prompt instructs the model to use only the provided context and never invent; fallback responses are used when context is empty or low-confidence. This limits but does not eliminate hallucination risk; treat as a stated product limitation.

---

## 6. Gating Switches (Feature Flags & Env)

| Switch | Effect |
|--------|--------|
| **`vector_search`** feature flag | Enables/disables vector retrieval in the public chatbot. |
| **`PINECONE_API_KEY`** | If set, vector backend is Pinecone; otherwise in-memory (e.g. `data/vector_db.pkl`). |
| **`OPENAI_API_KEY`** | Required for LLM and (depending on config) embeddings; affects LLM availability and embedding provider. |

These tie into automation readiness and BETA/SELLABLE status (see `scripts/automation_readiness.py`, `docs/AUTOMATION_READINESS.md`).

---

## 7. Contract Surfaces (What Clients Consume)

| Surface | Purpose |
|---------|--------|
| **Chatbot** | Public API: `POST /api/public/chatbot/query` (API key or widget token). |
| **Webhooks** | Tally/Typeform etc.: webhook intake and processing (see `core/webhook_api.py`, `core/webhook_intake_service.py`). |
| **Business / CRM** | Leads, pipeline, activities: `routes/business.py` (auth required). |
| **Knowledge / FAQ** | Chatbot builder: FAQ and KB CRUD under `core/chatbot_smart_faq_api.py` (e.g. `/knowledge/documents`, `/knowledge/document/<id>`). |

Use this as the API contract index for sales and support.

---

## 8. KB ↔ Vector Index Sync (Implemented)

- **Create:** `core/chatbot_smart_faq_api` persists FAQs and KB documents to the vector index and stores `metadata["vector_id"]` on the KB document.
- **Update / Delete:** Sync is implemented **inside the KB layer** (`core/knowledge_base_system.py`) so every update/delete path stays in sync:
  - **update_document(doc_id, updates):** After applying updates and updating the search index, if `document.metadata.vector_id` is present, calls `get_vector_search().update_document(vector_id, new_text, metadata)`.
  - **delete_document(doc_id):** Before removing the document, if `document.metadata.vector_id` is present, calls `get_vector_search().delete_document(vector_id)`; then performs the KB delete.
- **Fallback when `vector_id` missing:** On **update**, the KB layer self-heals: it re-adds the document to the vector index and stores the new `vector_id` in `document.metadata`, so future updates/deletes stay in sync. On **delete**, the KB doc is deleted and we log (no vector entry to remove). Vector backend failures (update/add/delete) are caught and logged; KB CRUD always succeeds.
- **Backend note:** The in-memory vector backend is fully synced. Pinecone-backed vector indexes use integer-like ids; if your Pinecone setup uses different semantics for update/delete, extend `MinimalVectorSearch` accordingly.
- **Multi-tenant / namespaces:** ✅ **IMPLEMENTED**: Tenant isolation is enforced in both vector search and KB search. Vector entries store `tenant_id` in metadata, and `search_similar()` filters by `tenant_id` parameter. The public chatbot extracts `tenant_id` from API key and passes it to both vector search (`search_similar(..., tenant_id=tenant_id)`) and KB search (`filters={'tenant_id': tenant_id}`). KB search's `_matches_filters()` checks `tenant_id` with highest priority. This prevents cross-tenant data leakage. See `docs/TENANT_ISOLATION_IMPLEMENTATION.md` for details.


---

*Last updated: Feb 2026*
