# Fikiri Site Bot — Phase 5b Handoff

Flag-gated Postgres transcript persistence and staff-only read API for the first-party marketing site bot.

## Delivered

| Area | Location | Notes |
|------|----------|-------|
| Tables | `site_chat_sessions`, `site_chat_messages`, `site_chat_transcript_reads` | Created via `ensure_site_chat_transcript_tables()` |
| Write path | `company_chatbot/transcript_store.py` | After successful `POST /api/site/chat/message` |
| Admin API | `routes/admin_site_chat_api.py` | JWT + owner/admin only |
| Reference SQL | `scripts/migrations/005_site_chat_transcripts.sql` | Ops reference; runtime bootstrap handles DDL |

## Feature flag

- `FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS=1` — enable writes (default **off**)
- `FIKIRI_SITE_BOT_TRANSCRIPT_RETENTION_DAYS=90` — purge helper cutoff
- Optional: `FIKIRI_SITE_BOT_TRANSCRIPT_HASH_SALT` — IP/UA hashing salt

## Admin endpoints (staff-only)

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/admin/site-chat/sessions` | Paginated summaries (`tier`, `mode`, `date_from`, `date_to`) |
| GET | `/api/admin/site-chat/sessions/<session_id>` | Full thread + audit `read` |
| GET | `/api/admin/site-chat/sessions/<session_id>/export` | Copy-friendly text (default) or `?format=json` + audit `export` |

Permission: `site_chat.read_transcripts` — enforced as **owner** or **admin** role (or `ADMIN_USER_IDS`).

## Write behavior

- Redis remains runtime session store (unchanged).
- Postgres is review/audit trail only.
- Transcript write failures are logged; chat response still returns `200`.
- IP and user-agent stored as salted SHA-256 hashes only.

## Retention

Call `purge_expired_transcripts()` from a scheduled job (not wired to cron in this slice). Deletes sessions with `last_seen_at` older than retention days.

## Test command

```bash
FIKIRI_SITE_BOT_TEST_MODE=1 python3 -m pytest \
  tests/test_company_chatbot_modes.py \
  tests/test_company_chatbot_grounding.py \
  tests/test_company_chatbot_intake.py \
  tests/test_company_chatbot_guards.py \
  tests/test_company_chatbot_scenarios.py \
  tests/test_company_chatbot_lead_scoring.py \
  tests/test_company_chatbot_session_store.py \
  tests/test_company_chatbot_rate_limit.py \
  tests/test_company_chatbot_transcript_store.py \
  tests/test_site_chatbot_api.py \
  tests/test_admin_site_chat_api.py -q
```

## Not in scope

- Admin UI page
- CRM / Slack / email
- LLM polish
- Tenant chatbot tables
- Bot intelligence changes
