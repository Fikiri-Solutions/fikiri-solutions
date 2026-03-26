# Launch-Critical Fixes (This Week)

Single reference for the four priorities that must work before real customers. See also [LAUNCH_SAFE_REMAINING.md](LAUNCH_SAFE_REMAINING.md) for full staging validation.

## Priority 1: Signup → Dashboard

**Flow:** Signup → token generation → login → dashboard access → API key generation.

**Status:**
- Signup uses `get_jwt_manager().generate_tokens()` in `routes/auth.py` (no stale import).
- Login uses `user_auth_manager.authenticate_user()` which returns tokens.
- Sessions: `secure_session_manager.create_session()` + cookie; JWT in response body.
- **Verify:** `pytest tests/test_auth_routes.py -v -k "login or signup"` then manual: signup → login → open dashboard → create API key.

## Priority 2: Widget → Lead Capture → CRM → Dashboard

**Flow:** Install widget/SDK on site → submit lead → `POST /api/webhooks/leads/capture` (with API key) → CRM lead created → visible in Dashboard/CRM.

**Implementation:**
- Webhook: `core/webhook_api.py` → `enhanced_crm_service.create_lead()` in `crm/service.py`.
- Dashboard/CRM: `GET /api/crm/leads` (routes/business.py) → `get_leads_summary()` → same `leads` table.
- **Fixes applied:** (1) Webhook and forms/submit now read `lead_id` from `result.get('data', {}).get('lead_id')` (CRM returns `{ success, data: { lead_id } }`). (2) CRM `create_lead` now resolves actual inserted row id after INSERT (was incorrectly using rowcount).

**Verify:** Use API key with scope `webhooks:leads` or `leads:create`, POST to `/api/webhooks/leads/capture` with `email`, optional `name`/`phone`/`source`, then confirm lead appears on CRM page.

## Priority 3: Idempotency Consistency

**Conflict resolved:** Pre-flight script previously reported "idempotency not implemented" while webhooks use idempotency.

**Reality:**
- **Implemented:** `core/idempotency_manager.py` (Redis + DB fallback), used by:
  - `core/webhook_api.py` (forms submit, lead capture) — server-generated deterministic keys from email/source/user_id.
  - `services/automation_queue.py`, `core/workflow_followups.py`, `core/automation_safety.py`, etc.
- **Client-provided key:** Not supported; keys are generated server-side. Optional future: accept `Idempotency-Key` header.

**Pre-flight:** Script now checks `core/idempotency_manager.py` and `core/webhook_api.py` so it correctly reports "Idempotency implemented".

## Priority 4: OAuth Token Encryption

**Status:** Implemented in `core/oauth_token_manager.py`.

- Fernet (from `cryptography.fernet`) when available; fallback base64-only when not.
- `encrypt_token` / `decrypt_token`; `store_tokens` writes `access_token_encrypted`, `refresh_token_encrypted`.
- Pre-flight script now checks for `Fernet|encrypt_token|decrypt_token` in that file.

**Production:** Set `OAUTH_ENCRYPTION_KEY` or rely on key derived from `SECRET_KEY` (see `_get_or_create_encryption_key`). Prefer explicit `OAUTH_ENCRYPTION_KEY` for rotation.

---

## What Can Wait

- Automation Studio stub actions (send_email, apply_label, etc.) — keep labeled "Not implemented" / "Partial".
- Social login (Gmail/GitHub) — leave disabled; email/password is sufficient for MVP.
- Analytics dashboard partial — not a blocker.
- SDK event hooks, WordPress `wp_enqueue_script`, Replit health check — polish later.

## Clean MVP Messaging

**Core:** AI chatbot, lead capture, CRM pipeline, website integration, webhook API, basic automations.

**Optional integrations:** Gmail, Outlook, Twilio, Slack, Stripe.

**Coming soon:** Advanced automation actions, full analytics, marketplace plugins, social login.

### Publish this exact framing in sales/pricing copy

| Bucket | What to say |
|---|---|
| **Verified now** | CRM, lead capture, webhook API, dashboard, core automation actions |
| **Optional integrations** | Gmail, Outlook, Twilio, Slack, Stripe (requires provider keys and setup) |
| **Coming soon / partial** | Automation actions currently marked `stub` or `partial` in Automation Studio capabilities |

Current stub actions to avoid overselling as "fully available":
- `send_email`
- `apply_label`
- `archive_email`
- `create_task`
