# Fikiri Site Bot — Production Readiness & Smoke

Use before soft launch or sales-review launch. Env var **names** only — set values in Render/Doppler/Vercel; never paste secrets into chat or commit them.

## Launch modes

### Soft launch (widget live, no durable transcripts)

| Variable | Value |
|----------|--------|
| `FIKIRI_SITE_BOT_ENABLED` | `true` |
| `FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS` | off / unset |
| `VITE_SITE_CHAT_WIDGET_ENABLED` | `true` |

Redis sessions, rate limits, grounding, intake, and lead scoring work. Staff cannot list/export Postgres transcripts.

### Sales-review launch (widget + staff transcript review)

| Variable | Value |
|----------|--------|
| `FIKIRI_SITE_BOT_ENABLED` | `true` |
| `FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS` | `1` |
| `FIKIRI_SITE_BOT_TRANSCRIPT_HASH_SALT` | strong random secret (required in production) |
| `FIKIRI_SITE_BOT_TRANSCRIPT_RETENTION_DAYS` | `90` (or your policy) |
| `VITE_SITE_CHAT_WIDGET_ENABLED` | `true` |

Enables append-only Postgres transcripts and staff admin read/export API. **Do not** rely on the internal dev default for `FIKIRI_SITE_BOT_TRANSCRIPT_HASH_SALT` in production.

---

## Production readiness pass (run before launch)

1. **Env vars** — Confirm Render (backend) and Vercel (frontend) match the chosen launch mode above; `REDIS_URL`, `CORS_ORIGINS`, rate-limit vars reviewed.
2. **Redis** — Deployed backend uses Redis for site chat sessions (restart worker or redeploy; continue same `session_id`).
3. **CORS** — Only real marketing domains in `CORS_ORIGINS` (and existing app CORS regex if used); preflight from prod origin succeeds on `/api/site/chat/message`.
4. **Widget flag** — `VITE_SITE_CHAT_WIDGET_ENABLED` on only where the bubble should appear.
5. **Transcript flag** — Soft launch: confirm no rows in `site_chat_*` after messages. Sales-review: confirm rows appear after messages; chat still returns `200` if DB write fails.
6. **Admin API** — Unauthenticated → `401`; member → `403`; owner/admin → list/read/export works; audit rows in `site_chat_transcript_reads`.
7. **Rate limits** — Normal conversation (session start + ~10 messages) stays under limits; burst in staging only → `429` + `Retry-After`.
8. **Secrets** — No `.env`, API keys, or salts in tracked files; `gitleaks` / `.gitignore` clean.
9. **Backend tests** — `FIKIRI_SITE_BOT_TEST_MODE=1` full site-bot pytest suite (see Phase 5a/5b handoff).
10. **Frontend** — `vitest` site chat tests, `tsc`, `npm run build`.

Then soft launch. Enable sales-review mode when staff need transcript review.

---

## Pre-deploy checklist

- [ ] Launch mode (soft vs sales-review) chosen and documented for ops.
- [ ] `REDIS_URL` (or Upstash Redis env) set on Render.
- [ ] `CORS_ORIGINS` includes production marketing origin(s).
- [ ] `FIKIRI_SITE_BOT_SESSION_TTL_SECONDS` reviewed (default `86400`).
- [ ] `FIKIRI_SITE_BOT_RATE_LIMIT_PER_MINUTE` / `FIKIRI_SITE_BOT_RATE_LIMIT_BURST` reviewed.
- [ ] If `FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS=1`: custom `FIKIRI_SITE_BOT_TRANSCRIPT_HASH_SALT` set.
- [ ] Backend boot logs: no `Site bot config:` warnings (see `validate_site_bot_runtime_config`).

## Post-deploy smoke (manual)

1. **Health** — App health route returns OK.
2. **Session start** — `POST /api/site/chat/session/start` → `200`, `schema_version` `v1`, `session_id` starts with `site_`.
3. **Message** — `POST /api/site/chat/message` → `200`, `mode`, `response`, `handoff`, `lead_assessment`.
4. **CORS** — Browser widget on marketing site: no CORS errors.
5. **Kill switch** — `FIKIRI_SITE_BOT_ENABLED=false` → `503` `SITE_BOT_DISABLED`.
6. **Rate limit** — Staging only: burst → `429` `RATE_LIMIT_EXCEEDED`.
7. **Redis** — Session survives backend restart (same `session_id` still valid).
8. **Transcripts** — If persist on: admin list shows session; export returns copy-friendly text.
9. **Regression** — Backend site-bot pytest suite green.

## Rollback

1. `FIKIRI_SITE_BOT_ENABLED=false` on API service.
2. Optionally `VITE_SITE_CHAT_WIDGET_ENABLED=false` on frontend build.
3. Redeploy; confirm `503 SITE_BOT_DISABLED` on chat routes.

## Explicitly deferred (do not add before soft launch)

- LLM polish
- CRM sync
- Slack/email alerts
- Admin transcript UI (API-only is enough for now)
- New modes / vector retrieval / service-lane expansion

## Out of scope

- Tenant embed chatbot (`/api/public/chat/*`, API keys).
