# Release notes — mailbox, Gmail sync, chatbot (2026-05-20)

## Gmail & sync

- OAuth lookback bridge: `lookback=1y` (etc.) on `/api/oauth/gmail/start` → stored in `oauth_states.metadata` → first sync uses `newer_than_days` (not hardcoded 90).
- Lookback UI: `GmailSyncOptions`, localStorage preset, passed from `GmailConnection`, `Onboarding`, and `Login`.
- Manual sync: `POST /api/crm/sync-gmail` with `core/gmail_sync_options.py` presets.
- **Fix:** `synced_emails` upsert on legacy SQLite (`ON CONFLICT (user_id, external_id, provider)`); idempotent index + dedupe migration.
- **Fix:** `crm_events` inserts on legacy SQLite (`tenant_user_id` NOT NULL).

## Mailbox / AI

- Email analyze/reply: longer frontend timeout, plain-text body for AI, schema alignment, analyze response cache.
- Unified email classification / intent taxonomy (see `docs/EMAIL_INTENT_TAXONOMY.md`).

## Chatbot

- Config, retrieval, vector chunk ingestion/cleanup, preview API, builder UX.

## Frontend / dev

- Vite: proxy only `/integrations/universal` to Flask (fixes `/integrations/gmail` OAuth return 404).
- `frontend/public/favicon.ico`.

## Tests

- `tests/test_synced_emails_upsert.py` (SQLite + optional Postgres via `FIKIRI_TEST_POSTGRES_URL`).
- OAuth lookback, onboarding jobs, gmail sync options, CRM event log, frontend lookback vitest.

## Deploy path

1. Merge PR into **`main`** on `Fikiri-Solutions/fikiri-solutions`.
2. Render **autoDeploy** (`render.yaml`: `branch: main`) → `fikiri-backend` + `fikiri-worker`.
3. Vercel frontend deploy (CI) from `main`.
4. **No manual Supabase migration** required for lookback (JSON metadata) or upsert index (`CREATE UNIQUE INDEX IF NOT EXISTS` on boot/upsert).

## Post-deploy checks

- Gmail OAuth with **Last year** selected → logs: `lookback_days=365`, `Fetching messages newer than 365 days`.
- Manual sync completes without `Email storage failed` / ON CONFLICT errors.
- CRM timeline: no `crm_events.tenant_user_id` spam in logs (legacy SQLite dev only).
