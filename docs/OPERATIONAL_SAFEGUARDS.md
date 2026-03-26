# Operational Safeguards (API Key, Webhooks, Widget, Health)

Reference for abuse prevention, database growth, webhook floods, widget robustness, and automation visibility.

## 1. API Key Abuse / Leaked Keys

**Risk:** Widget exposes API key in page source; someone could spam `POST /api/webhooks/leads/capture`.

**Implemented:**

- **Origin allowlist:** If `allowed_origins` is set on the API key, requests with `Origin`/`Referer` not in the list are rejected (403).
- **Rate limiting per API key:** After validating the key, we call `api_key_manager.check_rate_limit(api_key_id, 'minute')`. Default 60/min per key (configurable per key). If exceeded → **429** with `Retry-After: 60` and `error_code: RATE_LIMIT_EXCEEDED`.
- **Payload validation:**
  - Email required, valid format (regex), max **255** chars.
  - Name max **500** chars.
  - Reject with 400 and clear `error_code` (e.g. `INVALID_EMAIL`, `INVALID_PAYLOAD`).
- **Honeypot:** If payload (or `fields`) contains any of `honeypot`, `honeypot_field`, `_hp`, `website`, `url` and the value is non-empty, the request is treated as bot and rejected (we return 200 with a generic success message so bots don’t retry).

**Code:** `core/webhook_api.py` — `_check_webhook_rate_limit`, `_validate_webhook_email_and_name`, `_check_honeypot`; used in both `handle_form_submission` and `handle_lead_capture`.

## 2. Database Growth / Indexes

**Risk:** Large `leads` table without indexes slows CRM/dashboard queries.

**Implemented:**

- **Leads indexes** created at runtime in `core/database_optimization.py` → `_create_indexes`:
  - `idx_leads_user_id`
  - `idx_leads_email`
  - `idx_leads_created_at`

Migrations (e.g. `scripts/migrations/001_add_user_id_to_leads.py`) may add more; the above three are guaranteed on init.

## 3. Webhook Flood / Retry Storm

**Mitigations:**

- **Idempotency:** Server-generated deterministic keys (email + user_id + source) prevent duplicate leads from retries; duplicate submissions return 200 with `deduplicated: true`.
- **Rate limit:** 429 when per-key minute limit exceeded; client should respect `Retry-After`.
- **Request timeout:** Backend should run behind a reverse proxy (e.g. Render) with timeouts; SDK uses AbortController (e.g. 30s). Optional: add a server-side request timeout guard in front of heavy work.

**Recommendation:** Log 429 and repeated same-idempotency requests to detect retry storms.

## 4. Widget Breaking Client Sites

**Implemented:**

- **Safe init:** Auto-initialization from `data-fikiri-api-key` is wrapped in `try/catch`; errors are logged with `console.error('Fikiri widget error:', err)` and do not break the host page.
- **Async load:** SDK header recommends loading with `async`:  
  `<script async src=".../fikiri-sdk.js" data-fikiri-api-key="..."></script>`  
  so the script does not block rendering.

**Code:** `integrations/universal/fikiri-sdk.js`.

## 5. Automation Run Visibility (Silent Failures)

**Current state:**

- **Backend:** `automation_jobs` table and `services/automation_queue.py` track job state (queued, running, success, failed, retrying, dead). `automation_engine.get_execution_logs()` (and routes that use it) expose execution history per user/rule.
- **Dashboard:** Automation Studio can show queue health and execution results; “Recent executions” / execution logs can be wired to `GET /api/automation/logs` (or equivalent) so users see ✓/✗ and error messages.

**Recommendation:** Ensure the Automations UI has an “Automation log” or “Recent runs” section that displays at least: rule name, status (success/failed), error_message, created_at. Add a dedicated `automation_runs`-style table only if you need a simpler, lead-centric log (e.g. lead_id, automation_type, status, error_message); otherwise, existing execution logs are sufficient.

## 6. Health Endpoint

**Implemented:** `GET /api/health` returns:

- `status`: `"ok"` if database is connected, else `"degraded"`
- `database`: `"connected"` | `"disconnected"`
- `redis`: `"connected"` | `"disconnected"`
- Plus timestamp, version, service, environment.

Use for uptime checks and simple dependency visibility.

## 7. Request Logging (Recommendation)

Not fully implemented; recommended for production:

- **Webhook request log:** For each webhook request, log (e.g. structured JSON): timestamp, API key prefix (e.g. first 8 chars), origin, endpoint, status code, latency_ms. Do not log full API key or PII in plain text.
- **Tools:** Sentry, Logtail, or Datadog for exceptions and webhook errors; optional dedicated request log table or log drain for debugging client issues.

## 8. First-Customer Support

- Prefer **rapid hotfix** capability (e.g. branch + deploy), **error monitoring** (Sentry etc.), and a **customer support loop** (way to get logs or repro steps from the first customer) so edge cases and unexpected errors are visible and fixable quickly.
