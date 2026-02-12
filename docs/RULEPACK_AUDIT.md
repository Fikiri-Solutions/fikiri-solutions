# Fikiri Rulepack Audit

**Audit date:** Based on current codebase state  
**Rulepack version:** v4  
**Scope:** Backend (Python), Frontend (TypeScript/React), config, and structure

---

## 1. Architecture (Rules 0–1)

### 1.1 Domain boundaries
- **OK** Services call core/ and integrations/; routes use services or core as intended.
- **Gap** No `email_automation/pipeline.py`; rule references it. Email logic lives in `email_automation/actions.py`, `parser.py`, `service_manager.py`, `gmail_sync_jobs.py`, `jobs.py`. Consider adding a single pipeline entrypoint or updating the rule to match actual files.

### 1.2 CRM schema and workflows
- **Gap** Rule says: "Canonical CRM schema in `crm/schemas.py`". **No `crm/schemas.py` exists.** Lead/Contact structures live in `crm/service.py` (dataclasses).
- **Gap** Rule says: "All CRM mutations go through `crm/workflows/`". **No `crm/workflows/` directory.** Mutations are in `crm/service.py` and `crm/minimal_service.py`; routes and `core/automation_engine.py` import `crm.service.enhanced_crm_service` directly.
- **Recommendation:** Either (a) add `crm/schemas.py` with canonical Contact/Lead schema and `crm/workflows/` for mutations and update callers, or (b) update the rulepack to say schema lives in `crm/service.py` and mutations go through `crm/service.py` (no workflows folder).

---

## 2. AI pipelines (Rule 2)

### 2.1 Centralized LLM usage
- **OK** `core/ai/llm_router.py` and `core/ai/llm_client.py` implement the pipeline; `email_automation/ai_assistant.py`, `core/minimal_ai_assistant.py`, `email_automation/followup_system.py` use `LLMRouter`.
- **Violation** `core/minimal_vector_search.py` (lines 109–112) creates `openai.OpenAI()` and uses it directly for embeddings. Rule: "No direct OpenAI calls from routes, services, or frontend."
- **Recommendation:** Add an embedding path in `core/ai` (e.g. `llm_client.get_embedding()` or small `embedding_client.py`) and have `minimal_vector_search.py` call that instead of instantiating OpenAI directly.

### 2.2 Archive
- **OK** `archive/future-features/multi_language_support.py` contains direct OpenAI usage; archive is non-production, acceptable.

---

## 3. Redis (Rule 5)

### 3.1 Key format
- **OK** Most keys follow `fikiri:<domain>:<resource>:<id>` (e.g. `fikiri:session:`, `fikiri:jwt:session:`, `fikiri:email:jobs`, `fikiri:rate_limit:`, `fikiri:idempotency:`, `fikiri:ai:usage`).
- **Inconsistency** CRM/lead keys use both `fikiri:lead:*` and `fikiri:crm:stats` / `fikiri:lead:ids` (`crm/minimal_service.py`, `core/minimal_crm_service.py`). Rule suggests `fikiri:crm:contact:<id>`. Not blocking, but consider standardizing on `fikiri:crm:*` for all CRM-related keys.

### 3.2 Connection
- **OK** `core/redis_connection_helper.py` provides `get_redis_client()` and `_resolve_redis_url()`; callers use it or a shared client. No raw `Redis()` with hardcoded URLs in production paths.

---

## 4. Security (Rule 6)

### 4.1 Secrets
- **OK** No hardcoded API keys or passwords in repo; config/env used.
- **Frontend** Some frontend files hardcode the base URL (see Section 7); base URL is not a secret but should still go through config.

### 4.2 Auth on endpoints
- **OK** Auth routes and protected routes use JWT/session/rate limiting as intended.

---

## 5. Frontend (Rule 7)

### 5.1 API layer
- **Rule:** "All HTTP calls go through `frontend/src/api/client.ts` or a small typed API wrapper layer."
- **Reality:** No `frontend/src/api/client.ts`. There is `frontend/src/services/apiClient.ts` (axios) and `frontend/src/lib/api.ts` (fetch). Many components bypass this and call `fetch(config.apiUrl + ...)` or **hardcoded** `https://fikirisolutions.onrender.com/...` directly.
- **Hardcoded base URL (violation):**
  - `Login.tsx`: `fetch('https://fikirisolutions.onrender.com/api/auth/microsoft/connect', ...)`
  - `ForgotPassword.tsx`: `fetch('https://fikirisolutions.onrender.com/api/auth/forgot-password', ...)`
  - `ResetPassword.tsx`: `fetch('https://fikirisolutions.onrender.com/api/auth/reset-password', ...)`
  - `SyncProgress.tsx`: `fetch('https://fikirisolutions.onrender.com/api/onboarding/status?user_id=...')`
  - `PrivacySettings.tsx`: multiple `fetch('https://fikirisolutions.onrender.com/api/privacy/...')`
  - `Dashboard.tsx`: multiple `fetch('https://fikirisolutions.onrender.com/api/...')`
- **Recommendation:** (1) Introduce `frontend/src/api/client.ts` (or adopt `services/apiClient.ts` as the single client) that uses `config.apiUrl`. (2) Replace every direct `fetch(...)` to the backend with that client. (3) Remove all hardcoded `https://fikirisolutions.onrender.com` in favor of `config.apiUrl`.

### 5.2 TypeScript and structure
- **OK** TypeScript used; components are reasonably focused.

---

## 6. Logging (Rule 8)

### 6.1 Centralized logging
- **Rule:** "Use one logging utility in core/logging.py; do not create ad-hoc print/log statements."
- **Violation** Many files use `print()` for startup, errors, or debug: e.g. `app.py` (17), `core/redis_monitor.py` (23), `core/email_service_manager.py` (29), `email_automation/service_manager.py` (29), `integrations/gmail/utils.py` (35), plus routes, scripts, and other core modules.
- **Recommendation:** Replace `print()` in production code (app, core, routes, services, integrations, email_automation, crm, analytics) with the project’s logger (e.g. from `core.logging` or `core.enterprise_logging`). Keep `print()` only in scripts meant for CLI output.

---

## 7. Simplicity and naming (Rules 10, 15)

### 7.1 Naming
- **OK** Many modules use clear names (`llm_router`, `llm_client`, `redis_connection_helper`, `user_auth`, `jwt_auth`). Methods like `authenticate_user`, `get_redis_client`, `call_llm` are verb-based and clear.
- **Minor** Some generic names exist (e.g. `data`, `result`, `params`) in places; prefer more specific names when the scope isn’t tiny.

### 7.2 Simple classes/methods
- **OK** Core AI and auth are structured in a few focused classes and methods.
- **Watch** Large files (e.g. `crm/service.py`, `services/apiClient.ts`) have many responsibilities; consider splitting when adding features (e.g. by feature or by layer) to keep methods short and single-purpose.

### 7.3 Anti-bloat (Rule 14)
- **OK** No obvious "strategy/factory for the sake of it" or duplicate implementations of the same flow in one domain.
- **Note** Both `crm/service.py` (enhanced) and `crm/minimal_service.py` / `core/minimal_crm_service.py` exist; rule says "single, obvious implementation." Prefer one canonical CRM service and deprecate or remove the other once behavior is consolidated.

---

## 8. Performance and pagination (Rule 11)

### 8.1 Pagination
- **OK** CRM `get_leads_summary` uses `limit`/`offset`; list endpoints should be checked to ensure no unbounded lists. Audit did not find obvious unbounded list responses in main routes.

### 8.2 Async
- **Note** Backend is Flask (sync). Rule prefers async for I/O; this is a strategic choice. No change suggested in this audit.

---

## 9. Summary table

| Rule area              | Status   | Action |
|------------------------|----------|--------|
| CRM schema path        | Gap      | Add `crm/schemas.py` or update rule to match `crm/service.py` |
| CRM workflows path     | Gap      | Add `crm/workflows/` or update rule to "mutations via crm/service" |
| Email pipeline path    | Gap      | Add pipeline entrypoint or update rule to current email_automation files |
| Direct OpenAI (vector) | Violation | Route embeddings through core/ai |
| Frontend API layer     | Violation | Single API client; no hardcoded base URL |
| Logging vs print       | Violation | Replace print with logger in app/core/routes/services |
| Redis key naming       | Minor    | Prefer consistent `fikiri:crm:*` for CRM keys |
| Duplicate CRM impl    | Minor    | Converge on one CRM service and deprecate the other |

---

## 10. Recommended next steps (priority order)

1. **Frontend:** Introduce a single API client (e.g. `api/client.ts`) using `config.apiUrl` and replace all direct `fetch` and hardcoded Render URLs.
2. **Logging:** Replace `print()` with the project logger in `app.py`, core, routes, services, integrations, email_automation, crm, analytics.
3. **LLM:** Add an embedding API in `core/ai` and switch `core/minimal_vector_search.py` to use it instead of direct OpenAI.
4. **Rules:** Update rulepack to match reality: CRM schema and mutation paths, and email pipeline file names.
5. **CRM:** Decide canonical CRM service (e.g. `crm/service.py`) and migrate callers off minimal_service; then remove or archive the duplicate.
6. **Redis:** Optionally standardize CRM-related keys to `fikiri:crm:*` when touching that code.

This audit aligns with **Fikiri Solutions Rulepack v4** (simple classes/methods, intentional naming, no over-complication). Addressing the violations and gaps above will bring the codebase into full compliance.
