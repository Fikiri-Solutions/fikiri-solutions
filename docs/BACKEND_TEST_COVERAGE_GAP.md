# Backend Services – Unit Test Coverage Gap

**Exhaustive report:** routes, core, services, analytics, crm, email_automation.  
Aligned with `tests/` and codebase. **Test priorities mirror revenue‑critical and trust‑critical flows** (§1.1).

---

### Test status (last verified)

- **2026-02-12:** Verified `tests/test_business_routes.py::test_update_automation_rule_success` via `python3 -m unittest ...`.  
- **Note:** The full suite has **not** been re-run in this session. Use `pytest` or `python3 -m unittest` to validate all tests before release.

---

## 1.1 Test priorities (outcome‑driven order)

Priorities are ordered by **revenue impact** and **daily use**. Use this order when adding or extending tests.

### Highest priority (core revenue + daily use)

| Priority | Area | Modules to test | Why |
|----------|------|------------------|-----|
| **1** | **Lead capture → CRM** | `core/webhook_api.py`, `core/webhook_intake_service.py`, `crm/completion_api.py` | Tally/Typeform intake is how many users enter the system. Failures here lose money immediately. |
| **2** | **Inbox automation & sync** | `email_automation/actions.py`, `email_automation/parser.py`, `email_automation/pipeline.py`, `email_automation/service_manager.py`, Gmail client (e.g. `integrations/gmail/` or `core/gmail_client.py`) | Main value prop. If parsing or actions fail, automation breaks and users churn. |
| **3** | **CRM leads & pipeline** | `routes/business.py` (dedicated tests), `services/business_operations.py`, `services/automation_engine.py` (CRM actions) | Lead updates, pipeline view, and activities are everyday workflows. |

### Second tier (trust, safety, monetization)

| Priority | Area | Modules to test | Why |
|----------|------|------------------|-----|
| **4** | **Billing + Stripe** | `core/billing_api.py`, `core/billing_manager.py`, `core/fikiri_stripe_manager.py`, `core/stripe_webhooks.py` | Breaks revenue recognition and subscription state. |
| **5** | **Auth + session + rate limiting** | `core/secure_sessions.py`, `core/rate_limiter.py`, `core/idempotency_manager.py`, `core/security.py` | Prevents abuse and protects customer data. |
| **6** | **Analytics & monitoring** | `analytics/dashboard_api.py`, `analytics/monitoring_api.py` | Customers expect insight; also supports internal ops. |

### Lower priority (supporting systems)

| Priority | Area | Modules to test | Why |
|----------|------|------------------|-----|
| **7** | **AI / FAQ / Knowledge** | `core/smart_faq_system.py`, `core/knowledge_base_system.py`, `core/ai/*` | Useful but not core to the inbox/CRM pipeline. |
| **8** | **Appointments** | `routes/appointments.py`, appointments service, `core/appointment_reminders.py` | Secondary feature for most customers. |

---

## 1.2 Test build plan (execution checklist)

Order of work and target behaviors. Keep tests **pure unit** (mocks, no Flask client) for service layers; use **Flask test client** only for route contract + auth.

### Priority A — Finish “Lead capture → CRM”

You already test `core/webhook_api.py` and `crm/completion_api.py`. The remaining risk is logic inside the intake service.

| Add | Target behaviors (unit-level, no Flask client) |
|-----|-----------------------------------------------|
| **tests/test_webhook_intake_service.py** | ✅ Exists. Extend as needed: normalizes payloads (Tally vs Typeform → same internal shape), validates required fields (rejects/flags missing email/name), **deduping** (same email/phone doesn’t create duplicates), calls CRM/store with correct fields (mock DB/CRM), **idempotency** (same webhook event id won’t double-create), failure handling (invalid payload returns structured error). Treat intake service as pure function + minimal dependencies. |

### Priority B — Inbox automation (largest revenue-risk gap)

Sync jobs are tested; core “value prop” logic (parse → route → act) now has dedicated unit tests. Remaining gaps are limited to new/edge flows as they are added.

| Coverage | Target behaviors |
|-----|------------------|
| **tests/test_email_parser.py** ✅ | Parses typical Gmail payload into internal message model; handles HTML-only, missing subject, missing from, weird encodings; thread handling (if supported); attachment metadata (if applicable). |
| **tests/test_email_actions.py** ✅ | Archive / label / mark read / send reply routing correctness; **idempotency**: calling action twice doesn’t duplicate side effects; validates inputs (message id, thread id); handles Gmail client failures (retryable vs non-retryable). |
| **tests/test_email_pipeline.py** ✅ | `process_incoming()` calls parse → route → act in correct order; mock Gmail client + CRM + router/assistant; verify what gets logged/returned on success vs failure; ensure safety checks run before mutating actions (if applicable). |
| **tests/test_email_service_manager.py** ✅ | Provider selection / client init; handles missing credentials; no hardcoded provider config. |
| **tests/test_gmail_client.py** ✅ | Request building + error mapping only; no live Gmail calls. |

### Priority C — Extend routes/business.py coverage

| Extend | Add cases |
|--------|-----------|
| **tests/test_business_routes.py** | Attachments and any new business endpoints. **Rule:** route tests assert HTTP contract; service tests assert logic. |

### Fast test architecture (3 layers, keep separate)

1. **Pure unit tests (fastest):** Services as functions/classes with mocks; no Flask app.
2. **Blueprint/route tests:** Flask test client; contract + auth + status codes.
3. **Thin integration tests (optional):** Wiring only; never external APIs.

### Standard fixtures (conftest.py)

**Implemented in `tests/conftest.py`.** Use so every new test file has zero setup pain:

- `app` / `client` — Flask app test client (session- / function-scoped)
- `fake_redis` — in-memory Redis stub (`FakeRedis`)
- `mock_gmail_client` — mock for Gmail operations
- `mock_crm_service` — mock for CRM create_lead, get_lead, get_leads_summary, get_pipeline
- `mock_llm_router` — mock for AI route/analyze
- `caplog` — pytest built-in; use for log assertions

### Concrete “next 10 tests” (minimal set that closes largest risk)

| # | Test | File |
|---|------|------|
| 1 | webhook_intake_service: creates lead from Tally payload | test_webhook_intake_service.py |
| 2 | webhook_intake_service: dedup prevents second lead | test_webhook_intake_service.py |
| 3 | parser: handles HTML-only email | test_email_parser.py |
| 4 | parser: handles missing subject/from safely | test_email_parser.py |
| 5 | actions: archive calls Gmail client once with correct ids | test_email_actions.py |
| 6 | actions: idempotent archive does not double-call | test_email_actions.py |
| 7 | pipeline: happy path parse → classify → act | test_email_pipeline.py |
| 8 | pipeline: Gmail failure is handled and reported consistently | test_email_pipeline.py |
| 9 | business route: sync-gmail triggers job and returns status | test_business_routes.py |
| 10 | business route: pipeline endpoint returns paginated results | test_business_routes.py |

> These tests have been implemented in the repo. Re-run the suite to confirm they are green in your environment.

---

## 1. Currently tested (direct unit tests)

| Service / module | Test file |
|------------------|-----------|
| Auth routes (login, signup, etc.) | `tests/test_auth_routes.py` |
| User auth manager | `tests/test_user_auth.py` |
| JWT auth manager | `tests/test_jwt_auth.py` |
| OAuth token manager | `tests/test_oauth_token_manager.py` |
| CRM service (lead CRUD) | `tests/test_crm_service.py` |
| Gmail sync jobs | `tests/test_gmail_sync_jobs.py` |
| Inbox routes | `tests/test_inbox_routes.py` |
| Onboarding routes | `tests/test_onboarding_routes.py` |
| Integration framework | `tests/test_integration_framework.py` |
| Health checks | `tests/test_health_checks.py` |
| AI email analysis | `tests/test_ai_email_analysis.py` |
| API key manager | `tests/test_api_key_manager.py` |
| Public chatbot API | `tests/test_public_chatbot_api.py` |
| AI analysis API (contact/lead/business) | `tests/test_ai_analysis_api.py` |
| Vector persistence (FAQ/docs → vector index) | `tests/test_vector_persistence.py` |
| **Business routes** (leads, pipeline, activities, Gmail sync, email send/archive, auth) | `tests/test_business_routes.py` |
| **Webhook API** (Tally, Typeform) | `tests/test_webhook_api.py` |
| **Webhook intake service** (mapping, persistence) | `tests/test_webhook_intake_service.py` |
| **CRM completion API** (follow-ups) | `tests/test_crm_completion_api.py` |
| **Billing / Stripe** (blueprint, pricing, webhook handler) | `tests/test_billing_stripe.py` |
| **Secure sessions** | `tests/test_secure_sessions.py` |
| **Rate limiter** | `tests/test_rate_limiter.py` |
| **Idempotency manager** | `tests/test_idempotency_manager.py` |
| **Dashboard API** (debug, auth) | `tests/test_dashboard_api.py` |
| **Automation safety** | `tests/test_automation_safety.py` |
| **Automation engine** (services) | `tests/test_automation_engine.py` |
| **Email parser** | `tests/test_email_parser.py` |
| **Email actions** | `tests/test_email_actions.py` |
| **Email service manager** | `tests/test_email_service_manager.py` |
| **Email pipeline** | `tests/test_email_pipeline.py` |
| **Gmail client** | `tests/test_gmail_client.py` |

---

## 2. Partially tested (no dedicated test file)

| Service | How it’s exercised | Gap |
|--------|---------------------|-----|
| **routes/business.py** | Now has **dedicated** `test_business_routes.py` covering leads, pipeline, activities, Gmail sync, email send/archive, and automation endpoints (rules, suggestions, execute, safety, logs, test). | Extend tests for attachments and any new business endpoints. |
| **analytics/dashboard_api.py** | `test_dashboard_api.py` covers debug endpoint only. | Metrics and other dashboard endpoints untested. |
| **core/webhook_intake_service.py** | Now has **dedicated** `test_webhook_intake_service.py` (signature verification, mapping, persistence errors, Sheets failure handling). | Extend tests for optional connectors (e.g., Notion) if re-enabled. |

---

## 3. Missing unit tests (exhaustive by area)

### 3.1 Routes (`routes/`)

| Module | Notes |
|--------|--------|
| `routes/appointments.py` | Appointment CRUD, reminders |
| `routes/business.py` | See §2 – partial only |
| `routes/user.py` | User profile, settings |
| `routes/monitoring.py` | Monitoring routes |
| `routes/integrations.py` | Integrations API |
| `routes/test.py` | Dev/test routes (optional to test) |

### 3.2 Core (`core/`)

**API / HTTP layer**

| Module | Notes |
|--------|--------|
| `core/ai_chat_api.py` | Internal AI chat endpoints |
| `core/chatbot_smart_faq_api.py` | Only vector persistence tested; full FAQ/knowledge/conversation API untested |
| `core/billing_api.py` | Billing endpoints; ✅ basic coverage in `test_billing_stripe.py` |
| `core/webhook_api.py` | Webhook intake; ✅ `test_webhook_api.py` (Tally, Typeform) |
| `core/docs_forms_api.py` | Docs/forms API |
| `core/workflow_templates_api.py` | Workflow template CRUD |
| `analytics/dashboard_api.py` | Dashboard API (analytics) |
| `analytics/monitoring_api.py` | Monitoring dashboard API |
| `core/crm_completion_api.py` | CRM completion endpoints |
| `core/app_oauth.py` | OAuth flows (Google, Microsoft, etc.) |
| `core/app_onboarding.py` | Covered by `test_onboarding_routes.py` (onboarding *routes*); onboarding *core* logic not separately unit-tested |
| `core/dev_test_routes.py` | Dev-only (optional) |

**Services / business logic**

| Module | Notes |
|--------|--------|
| `core/appointments_service.py` | Appointment service logic |
| `core/appointment_reminders.py` | Reminder scheduling/logic |
| `core/automation_engine.py` | Automation execution (core); ✅ services layer in `test_automation_engine.py` |
| `core/automation_safety.py` | Safety checks for automation; ✅ `test_automation_safety.py` |
| `core/automated_followup_system.py` | Follow-up automation |
| `core/form_automation_system.py` | Form automation |
| `core/workflow_templates_system.py` | Workflow template system (backend of API) |
| `core/billing_manager.py` | Billing logic |
| `core/fikiri_stripe_manager.py` | Stripe integration |
| `core/stripe_webhooks.py` | Stripe webhook handling |

**Data / infra**

| Module | Notes |
|--------|--------|
| `core/database_optimization.py` | Used in tests (e.g. api_key_manager, integration_framework) but has no dedicated unit tests |
| `core/database_init.py` | DB init, health |
| `core/rate_limiter.py` | Rate limit checks and keys; ✅ `test_rate_limiter.py` |
| `core/secure_sessions.py` | Session create/validate; ✅ `test_secure_sessions.py` |
| `core/security.py` | Headers, CORS, rate-limit decorators |
| `core/idempotency_manager.py` | Idempotency keys and replay; ✅ `test_idempotency_manager.py` |
| `core/redis_connection_helper.py` | Redis connection |
| `core/redis_cache.py` | Redis cache layer |
| `core/redis_sessions.py` | Redis session store |
| `core/redis_pool.py` | Redis pool (if used) |
| `core/redis_queues.py` | Redis queues |
| `core/redis_monitor.py` | Redis monitoring |

**Domain / features**

| Module | Notes |
|--------|--------|
| `core/smart_faq_system.py` | FAQ search, add, categories |
| `core/knowledge_base_system.py` | Document search, add |
| `core/minimal_vector_search.py` | Vector add/search (Pinecone/local); only used indirectly in vector_persistence tests |
| `core/minimal_ml_scoring.py` | Lead scoring |
| `core/context_aware_responses.py` | Context-aware response logic |
| `core/multi_channel_support.py` | Multi-channel support |
| `core/reminders_alerts_system.py` | Reminders/alerts |
| `core/cleanup_scheduler.py` | Scheduled cleanup jobs |
| `core/feature_flags.py` | Feature flag evaluation |
| `core/api_validation.py` | Request validation helpers |
| `core/monitoring.py` | Monitoring setup |
| `core/performance_monitor.py` | Performance monitoring (only touched in integration test, not unit tests) |
| `core/privacy_manager.py` | Privacy logic |
| `core/error_handling.py` | Error handling helpers |
| `core/minimal_config.py` | Config |
| `core/minimal_auth.py` | Minimal auth helpers |
| `core/structured_logging.py` | Logging |
| `core/enterprise_logging.py` | Enterprise logging |

**AI / docs**

| Module | Notes |
|--------|--------|
| `core/ai/llm_client.py` | LLM client (no direct tests) |
| `core/ai/llm_router.py` | LLM router |
| `core/ai/embedding_client.py` | Embeddings |
| `core/ai/validators.py` | AI validators |
| `core/ai_document_processor.py` | Document processing |
| `core/document_analytics_system.py` | Document analytics |
| `core/document_templates_system.py` | Document templates |

**Other core**

| Module | Notes |
|--------|--------|
| `core/email_action_handlers.py` | Email action handling (core) |
| `core/onboarding_jobs.py` | Onboarding job logic |
| `core/gmail_client.py` | Gmail client; ✅ `tests/test_gmail_client.py` (integrations/gmail client coverage) |
| `core/google_sheets_connector.py` | Google Sheets |

**Integrations subpackage**

| Module | Notes |
|--------|--------|
| `core/integrations/integration_framework.py` | ✅ Has `test_integration_framework.py` |
| `core/integrations/calendar/google_calendar_provider.py` | Used in integration framework tests |
| `core/integrations/calendar/calendar_manager.py` | No direct tests |
| `core/integrations/cleanup_jobs.py` | No direct tests |

---

### 3.3 Services (`services/`)

**No dedicated unit tests for most services modules, except automation engine (and business_operations partially via business routes).** Do not regress on existing coverage.

| Module | Notes |
|--------|--------|
| `services/automation_engine.py` | ✅ `test_automation_engine.py` (handlers, get_automation_rules) |
| `services/business_operations.py` | Partial via business routes tests; no dedicated service-layer unit tests |
| `services/email_action_handlers.py` | Email action handlers (service layer); no unit tests |

---

### 3.4 Analytics (`analytics/`)

| Module | Notes |
|--------|--------|
| `analytics/dashboard_api.py` | Dashboard metrics/analytics API; ✅ debug endpoint in `test_dashboard_api.py` |
| `analytics/monitoring_api.py` | Monitoring API |
| `analytics/document_analytics.py` | Document analytics |

---

### 3.5 CRM (`crm/`)

| Module | Notes |
|--------|--------|
| `crm/service.py` | ✅ Has `tests/test_crm_service.py` |
| `crm/completion_api.py` | CRM completion API; ✅ `test_crm_completion_api.py` (follow-ups create/process) |

---

### 3.6 Email automation (`email_automation/`)

| Module | Notes |
|--------|--------|
| `email_automation/gmail_sync_jobs.py` | ✅ Has `tests/test_gmail_sync_jobs.py` |
| `email_automation/ai_assistant.py` | Only used indirectly; no direct unit tests |
| `email_automation/actions.py` | ✅ `tests/test_email_actions.py` |
| `email_automation/followup_system.py` | No unit tests |
| `email_automation/jobs.py` | No unit tests |
| `email_automation/parser.py` | ✅ `tests/test_email_parser.py` |
| `email_automation/pipeline.py` | ✅ `tests/test_email_pipeline.py` |
| `email_automation/service_manager.py` | ✅ `tests/test_email_service_manager.py` |

---

## 4. Priority suggestion for adding tests

Follow **§1.1 Test priorities (outcome‑driven order)** as the canonical order. Below maps that to done vs remaining.

**Highest priority (revenue + daily use)**  
- **Lead capture → CRM:** `webhook_api.py` ✅, `webhook_intake_service.py` ✅, `crm_completion_api.py` ✅.  
- **Inbox automation & sync:** ✅ `email_automation/actions.py` — `tests/test_email_actions.py`; ✅ `email_automation/parser.py` — `tests/test_email_parser.py`; ✅ `email_automation/service_manager.py` — `tests/test_email_service_manager.py`; ✅ `email_automation/pipeline.py` — `tests/test_email_pipeline.py`; ✅ Gmail client — `tests/test_gmail_client.py` (integrations/gmail client).  
- **CRM leads & pipeline:** `routes/business.py` ✅ (dedicated), `services/automation_engine.py` ✅. **Still missing:** deeper `services/business_operations.py` dedicated unit tests.  

**Second tier (trust, safety, monetization)**  
- **Billing + Stripe:** `billing_api.py` / Stripe handler ✅ (basic). **Still missing:** `billing_manager.py`, `stripe_webhooks.py` payload handling.  
- **Auth + session + rate limiting:** `secure_sessions.py` ✅, `rate_limiter.py` ✅, `idempotency_manager.py` ✅. **Still missing:** `security.py` (middleware/decorators).  
- **Analytics & monitoring:** `dashboard_api.py` ✅ (debug). **Still missing:** full dashboard metrics, `monitoring_api.py`.

**Lower priority (supporting)**  
- **AI / FAQ / Knowledge:** `smart_faq_system.py`, `knowledge_base_system.py`, `core/ai/*` – add when capacity allows.  
- **Appointments:** `routes/appointments.py`, appointment service, `appointment_reminders.py` – secondary.

---

## 5. Summary

- **Test priorities:** See **§1.1** for the canonical outcome‑driven order (lead capture → CRM, inbox automation, CRM/pipeline, then billing/auth/analytics, then AI/appointments).  
- **Tested:** Auth routes, user_auth, JWT, OAuth token manager, CRM service, Gmail sync jobs, inbox routes, onboarding routes, integration framework, health checks, AI email analysis, public API suite (API key manager, public chatbot, AI analysis API, vector persistence). **Plus:** business routes, webhook API, CRM completion API, billing/Stripe (basic), secure_sessions, rate_limiter, idempotency_manager, dashboard_api (debug), automation_safety, automation_engine.  
- **Partially tested:** `routes/business.py` (dedicated test file; still missing attachments), `webhook_intake_service` (dedicated tests; optional connectors remain), dashboard (debug only).  
- **Missing (highest impact):** `services/business_operations.py` dedicated unit tests.  
- **Missing (second tier):** `billing_manager.py`, full `stripe_webhooks.py` payload handling, `security.py`, full dashboard metrics, `monitoring_api.py`.  
- **Missing (lower):** FAQ/knowledge, AI modules, appointments, and the rest listed in §3.

Use **§1.1** to order work; use this list to add or extend unit tests where still missing.
