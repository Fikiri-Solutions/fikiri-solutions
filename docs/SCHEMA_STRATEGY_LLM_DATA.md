# Schema Strategy for LLM Routing and Data Ingestion

How to structure schemas so that all integrations, automations, and client uploads feed the LLM router with consistent, well-shaped data.

---

## 1. Goal

- **One canonical shape per domain** (Lead, KnowledgeSnippet, EmailClassification, etc.) so every entry point normalizes to it before storage or before calling the LLM.
- **One standard “context” shape** passed into the LLM router so preprocessing, logging, and model selection are predictable.
- **Output schemas** for each intent in one place so validation and LLM instructions stay aligned.

Result: fewer ad-hoc dicts, consistent prompts, and the right context reaching the right model.

---

## 2. Current Data Flows (Summary)

| Source | Where it lands | Shape today | Consumed by LLM as |
|--------|----------------|-------------|--------------------|
| CRM CSV/JSON import | `leads` table via `crm/service.py` | Canonical lead fields (email, name, phone, company, source, stage, score, …) | Lead analysis: free-form dict in prompt |
| Chatbot KB (FAQ, docs, CSV/XLSX upload) | `faq` table, `knowledge_base` / vector store | FAQ: question, answer, category; KB: title, content, category; vector: content | Snippets string in prompt (`_build_context_snippets`) |
| Email (Gmail/Outlook, pipeline) | Classification → intent, then contact extraction | `CLASSIFICATION_SCHEMA`, `CONTACT_SCHEMA` in `email_automation/ai_assistant.py` | Email reply / classification prompts |
| Document processing (PDF, DOCX, CSV, XLSX) | Extracted text → KB or inline use | Plain text + metadata (file_type, etc.) | Fed into KB → same as “Chatbot KB” |
| Workflows / dashboard | Tables, analytics | Various | Ad-hoc in prompts |

The router today takes `input_data` (string), optional `intent`, optional `context` (dict), and optional `output_schema`. Only `context.get('context', '')` is appended to the prompt; the rest is for callers’ own use.

---

## 3. Recommended Schema Layout

### 3.1 Canonical domain schemas (single source of truth)

Define these in **one module** (e.g. `core/ai/schemas.py`) and use them for:

- Validation at ingestion (e.g. CSV/JSON import → Lead).
- Type hints and docs.
- Building prompts and context for the LLM.

| Schema | Purpose | Used by |
|--------|---------|--------|
| **Lead** | CRM contact/lead. Fields: id?, user_id?, email, name, phone?, company?, source?, stage?, score?, created_at?, updated_at?, notes?, tags?, metadata?. | CRM import, lead analysis API, Gmail sync → CRM |
| **KnowledgeSnippet** | Single retrievable unit for chatbot. `type`: `faq` \| `knowledge_base` \| `vector`; `content` (string); optional `title`, `question`, `answer`, `source_id`. | FAQ/KB/vector search → `_build_context_snippets` → prompt |
| **EmailClassificationResult** | Result of email intent classification. `intent`, `confidence`, `urgency`, `suggested_action`. | Email pipeline → LLM classification → downstream actions |
| **ExtractedContact** | Contact info from email or form. `email`, `name?`, `phone?`, `company?`, etc. | Email pipeline, lead capture |

Canonical **output** schemas for the LLM (also in `core/ai/schemas.py`):

| Schema | Intent | Required fields |
|--------|--------|------------------|
| **ChatbotResponseSchema** | `chatbot_response` | answer, confidence, fallback_used, sources; optional follow_up |
| **EmailClassificationSchema** | `classification` (email) | intent, confidence, urgency, suggested_action |
| **LeadAnalysisSchema** | Lead analysis (custom intent) | score, conversion_probability, priority, recommended_actions, insights, next_steps, estimated_value |

All entry points that **produce** data for these domains should normalize to the canonical shape before writing to DB or before calling the router. All callers that **consume** LLM output should use the same output_schema from this module.

### 3.2 LLM context contract (what to pass to the router)

Standardize the `context` dict passed to `LLMRouter.process()` so preprocessing and logging are consistent:

- **`context_text`** (or keep **`context`**): string that gets appended to the prompt (snippets, lead summary, etc.). Preprocess should use this so every caller passes “what the model should see” in one key.
- **`tenant_id`**, **`user_id`**: for logging and multi-tenant isolation.
- **`intent`**: can be set by caller; used for model selection and logging.
- **`source`**: optional (e.g. `chatbot`, `email_pipeline`, `ai_chat`, `lead_analysis`) for analytics.

No need to change the router’s function signature; just document and use this shape everywhere so that e.g. chatbot, email, and lead analysis all pass the same structure and the router can reliably inject `context_text` / `context` into the prompt.

### 3.3 Intent → model mapping (router)

Keep **one place** for intent → model/tokens/temperature (already in `core/ai/llm_router.py` `choose_model`). Add any missing intents used by the product (e.g. `chatbot_response`) so they get the right model and bounds. Document the list of intents and which output_schema each uses (see table above).

---

## 4. Ingestion → Canonical Schema (Efficient Flow)

- **CRM**: CSV/JSON import and any sync (e.g. Gmail) already write through `crm/service.py`. Ensure all paths use the same Lead field set (email, name, phone, company, source, stage, etc.) and reject or normalize unknowns. No second “import schema”; the canonical Lead is the import schema.
- **Chatbot KB**: FAQ, knowledge_base, and vector store should expose a **unified “snippet” shape** (type + content + optional title/question/answer/source_id). `_build_context_snippets` and any new retrieval code should produce a list of KnowledgeSnippet-like dicts, then turn them into one context string. Document upload (PDF, DOCX, CSV, XLSX) → extracted text → store as KB item in that same shape.
- **Email**: Pipeline already produces classification + optional contact extraction. Use `EmailClassificationSchema` and `ExtractedContact` (or Lead) from the central schemas; merge extracted contact into CRM via `crm/service.py` so it becomes a canonical Lead.

This keeps “schema” meaning: **at the boundary (API/upload/sync), normalize to the canonical domain schema; then store or pass to the LLM only that shape.**

---

## 5. What to Implement (Concrete)

**Phased rollout (recommended):**

- **Phase 1 (done):**  
  - `core/ai/schemas.py` — LLM only: ChatbotResponseSchema, EmailClassificationSchema, LeadAnalysisSchema, build_llm_context.  
  - `core/domain/schemas.py` — Placeholder for Phase 2 (Lead, KnowledgeSnippet, ExtractedContact).  
  - Callers: public_chatbot_api.py, email_automation/ai_assistant.py, ai_analysis_api.py use central output schemas; router supports context_text and chatbot_response intent.

- **Phase 2a (done):**  
  - `core/domain/schemas.py`: Lead (LEAD_CANONICAL_FIELDS, normalize_lead_payload, lead_has_required_for_create), KnowledgeSnippet (knowledge_snippet, snippets_to_context_string), ExtractedContact (normalize_extracted_contact, extracted_contact_to_lead_payload).  
- **Phase 2b (done):** CRM import (CSV and JSON) uses `normalize_lead_payload` before `import_leads`. Chatbot uses `_sources_to_snippets` → `snippets_to_context_string` (domain). Email `extract_contact_info` returns `normalize_extracted_contact(parsed_result)`.

- **Phase 3 (done):**  
  - Router: `INTENT_MODEL_CONFIG` and `KNOWN_INTENTS` at module level in `core/ai/llm_router.py`; `choose_model` uses them. Logging includes `source`, `tenant_id`, `user_id` from context when present (success, error, and schema_validation_failed).

**Structure:**  
- **core/ai/schemas.py** = LLM output schemas + context builder (no business-domain models).  
- **core/domain/schemas.py** = canonical business objects (Lead, KnowledgeSnippet, etc.) used by CRM, imports, integrations — not AI-only.

---

## 6. Where this can cause issues or conflicts

### 6.1 Context: double-appended prompt text

The router’s **preprocess** appends `context_text` or `context` to the prompt. Several callers (e.g. public chatbot, email assistant) **do not** pass those keys; they put all context **inside** `input_data` (the prompt string). That’s fine.

**Conflict:** If a caller both (a) embeds context in the prompt and (b) passes the same text in `context_text`/`context`, the model will see that context **twice**. When adopting `build_llm_context()`, use **one** of: embed context in the prompt and pass metadata-only in `context`, **or** pass the text in `context_text` and keep the prompt minimal. Don’t do both for the same content.

### 6.2 Intent namespace

`choose_model` only knows a fixed set of intents (`email_reply`, `classification`, `chatbot_response`, `general`, etc.). Any other intent (e.g. `pricing_inquiry` from context_aware_responses) falls through to `general`. So:

- Intents used with `LLMRouter.process()` should match the router’s intent list (or stay as `general`).
- Other systems (e.g. context_aware_responses) can use their own intent names; they only conflict if someone passes those names into the router and expects custom model/tokens.

### 6.3 Schema semantics when unifying (e.g. contact extraction)

`email_automation/ai_assistant.py` uses **CONTACT_SCHEMA** with **required** fields: phone, company, website, location, budget, timeline. `core/ai/schemas.py` defines **EXTRACTED_CONTACT_SCHEMA** with **all properties optional**. If you replace the email assistant’s schema with the central one without aligning required fields, validation may start accepting empty or partial objects and downstream code might break. When unifying, either keep the same required/optional rules or update all consumers.

### 6.4 Canonical Lead fields and strict validation

**LEAD_CANONICAL_FIELDS** is a list of known lead attributes. Using it as a **whitelist for what to send to the LLM** is safe. Using it as **strict validation at ingestion** (rejecting any key not in the list) can break:

- Integrations that add custom or tenant-specific fields.
- Future new fields added to the CRM.

Prefer: validate required fields (e.g. email, name) and allow extra keys, or normalize into a “for LLM” subset instead of rejecting.

### 6.5 Circular imports

**core/ai/schemas.py** is kept dependency-light (no imports from `core.public_chatbot_api`, routes, or heavy app modules). If you add imports there from modules that eventually import `core.ai`, you can get a circular import. Keep schemas as pure data and helpers; any loading of config or services should stay in the callers.

### 6.6 Output schema vs. actual LLM response

The **SchemaValidator** checks that the LLM output matches the given `output_schema`. If the prompt asks for slightly different JSON (e.g. different field names or types), validation can fail even when the answer is usable. Keep prompt instructions (e.g. “Return JSON with fields: answer, confidence, …”) in sync with the schema used for that intent. Centralizing schemas helps, but the prompts that generate the output must stay aligned.

---

## 7. Benefits

- **LLM routing works well**: Same context contract and intents everywhere; model selection and token limits stay consistent.  
- **Fewer bugs**: One canonical shape per domain; validation at ingestion and at LLM output.  
- **Easier to add integrations**: New upload or sync only needs to normalize to Lead or KnowledgeSnippet (or the right output_schema) and call the router with the standard context shape.  
- **Clear ownership**: Schemas live in `core/ai/schemas.py`; ingestion lives in crm/, email_automation/, and doc/KB pipelines; router stays generic and intent-driven.
