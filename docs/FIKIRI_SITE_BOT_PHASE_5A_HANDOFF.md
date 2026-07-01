# Fikiri Site Bot — Phase 5a Handoff

Production hardening for the first-party marketing site assistant (`/api/site/chat/*`). No transcript persistence, CRM, Slack/email, or bot intelligence changes.

## Delivered

| Area | Module / route | Notes |
|------|----------------|-------|
| Redis sessions | `company_chatbot/session_store.py` | Key `fikiri:site_chat:session:<id>`; TTL via `FIKIRI_SITE_BOT_SESSION_TTL_SECONDS` |
| Rate limits | `company_chatbot/rate_limit.py` | Token bucket; scoped to site chat routes only |
| Kill switch | `company_chatbot/config.py`, `routes/site_chatbot_api.py` | `FIKIRI_SITE_BOT_ENABLED=false` → 503 `SITE_BOT_DISABLED` |
| Env validation | `company_chatbot/config.py` | Warns on missing `REDIS_URL` / `CORS_ORIGINS` in production |
| Smoke checklist | `docs/FIKIRI_SITE_BOT_PRODUCTION_SMOKE.md` | Pre/post deploy steps |

## Architecture

```
POST /api/site/chat/session/start
POST /api/site/chat/message
        ↓
routes/site_chatbot_api.py  (kill switch, rate limit, no API key)
        ↓
company_chatbot/orchestrator.py
        ↓
company_chatbot/session_store.py  → Redis (or in-memory fallback)
```

## Env vars (names only)

| Variable | Default | Purpose |
|----------|---------|---------|
| `FIKIRI_SITE_BOT_ENABLED` | on | Backend kill switch |
| `FIKIRI_SITE_BOT_TEST_MODE` | off | Deterministic tests; in-memory session/rate-limit fallback |
| `FIKIRI_SITE_BOT_SESSION_TTL_SECONDS` | `86400` | Redis session TTL |
| `FIKIRI_SITE_BOT_RATE_LIMIT_PER_MINUTE` | `20` | Sustained refill rate |
| `FIKIRI_SITE_BOT_RATE_LIMIT_BURST` | `40` | Token bucket capacity |
| `REDIS_URL` | — | Shared app Redis (recommended in production) |
| `CORS_ORIGINS` | — | Marketing site origin(s) for browser calls |
| `VITE_SITE_CHAT_WIDGET_ENABLED` | on | Frontend widget gate (unchanged) |

## HTTP contracts (unchanged schema)

- Success responses still include `schema_version: "v1"`.
- No API key on site bot routes.
- `429` + `RATE_LIMIT_EXCEEDED` + `Retry-After` when limited.
- `503` + `SITE_BOT_DISABLED` when kill switch off.

## Explicitly not in 5a

- `FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS` (Phase 5b)
- Staff transcript UI, CRM, Slack/email, LLM polish, mode/grounding/intake changes

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
  tests/test_site_chatbot_api.py -q
```

## Follow-up (optional)

- Frontend: show friendly copy when API returns `SITE_BOT_DISABLED` or `RATE_LIMIT_EXCEEDED` (widget unchanged in 5a).
- Phase 5b: Postgres transcripts behind `FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS=1`.
