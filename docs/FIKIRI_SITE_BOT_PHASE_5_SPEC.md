# Fikiri Site Bot Phase 5 Spec — Production Hardening

**Status:** Spec only (no implementation yet)  
**Prior:** [FIKIRI_SITE_BOT_PHASE_4_HANDOFF.md](./FIKIRI_SITE_BOT_PHASE_4_HANDOFF.md)  
**Rules:** [FIKIRI_SITE_BOT_ENGINEERING_RULES.md](./FIKIRI_SITE_BOT_ENGINEERING_RULES.md)

---

## Phase 4 closure (verified locally)

Phase 4 is **production-ready from a widget standpoint** after local verification:

| Check | Result |
|-------|--------|
| `npm install` | Passed |
| Widget vitest suite (6 tests) | Passed |
| `npx tsc --noEmit` | Passed |
| `npm run build` | Passed |
| Backend site-bot suite | 65 passed (includes conversational UX fix) |

Architecture separation remains unchanged:

```
Marketing pages → MarketingChatWidget → FikiriSiteChatWidget → siteChatApi → /api/site/chat/* → company_chatbot/
Tenant embed    → PublicChatbotWidget → public_chatbot_api → core/chatbot_*
```

---

## Phase 5 goal

Make the **first-party marketing bot safe to run in production** on Render + Vercel without changing intelligence, intake logic, KB, or tenant chatbot code.

**In scope:** operational reliability, abuse controls, session durability, optional transcript retention, staff-safe read path, env/CORS/deployment gates, smoke checklist.

**Explicitly out of scope (Phase 6+):**

- LLM polish (`FIKIRI_SITE_BOT_LLM_POLISH`)
- CRM lead write / Salesforce-style pipelines
- Slack or email notifications
- New bot modes or KB expansion
- Changes to `PublicChatbotWidget`, `core/public_chatbot_api.py`, or tenant chatbot builder

---

## Current production gaps

| Gap | Risk today |
|-----|------------|
| Sessions in process memory (`company_chatbot/orchestrator.py`) | Lost on restart, not shared across Gunicorn workers |
| No route-level rate limits on `/api/site/chat/*` | Cheap to spam; Redis rate limiter exists but unused here |
| No transcript persistence | Staff cannot review widget conversations; no post-mortem |
| No admin read API | Even if stored, nothing to query safely |
| No feature kill switch on backend | Frontend `VITE_SITE_CHAT_WIDGET_ENABLED` hides UI only |
| CORS relies on global app config | Must confirm `fikirisolutions.com` + preview origins |

---

## Decision: transcript storage for first deployment

### Options considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A — Stateless launch** | Redis sessions only; no Postgres transcripts | Smallest blast radius; no PII retention policy yet | No staff visibility; harder to debug prod issues |
| **B — Postgres now (dedicated tables)** | Append-only `site_chat_*` tables, separate from tenant `chatbot_*` | Clean domain boundary; staff view possible; audit trail | Retention/PII policy required before enabling |
| **C — Reuse tenant tables** | Write with fixed `tenant_id=fikiri_company` | Reuses `chatbot_conversation_store.py` | Violates separation; couples marketing bot to tenant product schema |

### Recommendation: **A for launch, B in the same phase behind a flag**

Ship production in two slices within Phase 5:

1. **Slice 5a (required for go-live):** Redis session store + rate limits + backend kill switch + CORS/env validation + smoke checklist. **No Postgres transcripts.**
2. **Slice 5b (same phase, optional enable):** Dedicated Postgres transcript tables + staff read endpoint. **Default off** until retention policy is documented and one person confirms staff access works.

**Do not reuse** `chatbot_conversations` / `chatbot_messages` for the company site bot. Tenant persistence (`core/chatbot_conversation_store.py`) is tenant-scoped product infrastructure; the site bot lives in `company_chatbot/` with its own tables or none at all.

**Rationale:** The real production blocker is **session durability across workers/restarts**, not transcripts. Transcripts are valuable for sales follow-up but not required for the widget to function. A flag-gated Postgres path avoids blocking launch while keeping the architecture clean.

---

## Work packages

### 5.1 — Redis session store (required)

**Problem:** In-memory `_SESSIONS` breaks on deploy/restart and with multiple Gunicorn workers.

**Proposal:**

- New module: `company_chatbot/session_store.py`
- Redis key format: `fikiri:site_chat:session:<session_id>`
- Serialize: turn count, intake state, slots, response history (bounded), last mode, timestamps
- TTL: **24 hours** idle (configurable via `FIKIRI_SITE_BOT_SESSION_TTL_SECONDS`, default `86400`)
- Fallback: in-memory only when Redis unavailable **in development**; in production, log warning and still accept sessions (degraded) OR fail session start — **recommend fail closed in production** if Redis is required elsewhere already

**Acceptance:**

- Session survives simulated worker restart (Redis flush of one key, not whole store)
- Unknown/expired session returns `404 SESSION_NOT_FOUND` (unchanged contract)
- Existing orchestrator tests pass with injectable store (memory for tests)

---

### 5.2 — Rate limiting (required)

**Proposal:**

- Apply limits on:
  - `POST /api/site/chat/session/start` — e.g. **10 / hour / IP**
  - `POST /api/site/chat/message` — e.g. **60 / hour / IP**, **20 / minute / session_id**
- Use existing `core/rate_limiter.py` or Flask-Limiter patterns already on app
- Key prefix: `fikiri:ratelimit:site_chat:<route>:<ip_or_session>`
- Return `429` with stable error code (`RATE_LIMIT_EXCEEDED`), friendly message for widget

**Acceptance:**

- Integration test: burst over limit → 429
- Normal conversation under limits → unchanged 200 behavior
- OPTIONS preflight not rate limited

---

### 5.3 — Backend feature flags (required)

| Env var | Default | Purpose |
|---------|---------|---------|
| `FIKIRI_SITE_BOT_ENABLED` | `1` | Kill switch for both routes (503 or 404 when off) |
| `FIKIRI_SITE_BOT_SESSION_TTL_SECONDS` | `86400` | Redis session TTL |
| `FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS` | `0` | Append-only Postgres transcripts (Slice 5b) |
| `FIKIRI_SITE_BOT_TRANSCRIPT_RETENTION_DAYS` | `90` | Cleanup job when persist enabled |

Frontend gate (`VITE_SITE_CHAT_WIDGET_ENABLED`) remains; backend flag is the authoritative off switch.

**Acceptance:**

- Widget API returns clear error when disabled; widget shows friendly “chat unavailable” (small frontend follow-up in Phase 5)

---

### 5.4 — Transcript storage (optional slice, flag-gated)

**When `FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS=1`:**

New tables (additive migration, Postgres + SQLite compat for local tests):

```text
site_chat_sessions
  id, session_id (unique), created_at, last_activity_at,
  ip_hash, user_agent_hash, page_url (optional),
  intake_completed, final_mode, handoff_type

site_chat_messages
  id, session_id, role (user|assistant), content,
  mode, grounded, confidence, sources_json,
  guard_triggered, created_at
```

**Write path:** fire-and-forget after `handle_message` succeeds; never block response on DB failure (log + metric).

**Do not store:** raw IP (hash only), full retrieval debug blobs, secrets.

**Retention:** scheduled cleanup deletes rows older than `FIKIRI_SITE_BOT_TRANSCRIPT_RETENTION_DAYS`.

---

### 5.5 — Staff transcript view (optional slice, requires 5.4)

**Proposal:**

- `GET /api/admin/site-chat/sessions` — paginated list (capability: `site_chat.read_transcripts`)
- `GET /api/admin/site-chat/sessions/<session_id>` — messages for one session
- JWT + RBAC only; no public access
- Audit log each read (`site_chat.transcript_view`)

**UI:** defer full `/admin` page to Phase 5b or 6; API + curl/Postman smoke is enough for first staff use.

**Acceptance:**

- Non-admin → 403
- Admin → paginated sessions, redacted hashes only

---

### 5.6 — CORS and environment validation (required)

**Checklist before prod:**

- [ ] `CORS_ORIGINS` includes `https://fikirisolutions.com`, `https://www.fikirisolutions.com`
- [ ] Vercel preview pattern already in app CORS regex (verify)
- [ ] `VITE_API_URL` on Vercel points to Render backend
- [ ] Render has `FIKIRI_SITE_BOT_ENABLED=1`
- [ ] Redis URL present (session + rate limit)

**Acceptance:**

- Preflight from production origin succeeds on `/api/site/chat/message`
- Local dev still works on `localhost:5174` and LAN IPs

---

### 5.7 — Deployment and smoke checklist (required)

Document in `docs/FIKIRI_SITE_BOT_PRODUCTION_SMOKE.md` (create during implementation):

**Pre-deploy**

```bash
# Backend
FIKIRI_SITE_BOT_TEST_MODE=1 python3 -m pytest tests/test_company_chatbot_*.py tests/test_site_chatbot_api.py -q

# Frontend
cd frontend && npx vitest run src/__tests__/siteChatApi.test.ts \
  src/__tests__/FikiriSiteChatWidget.test.tsx \
  src/__tests__/MarketingChatWidget.test.tsx
cd frontend && npx tsc --noEmit && npm run build
```

**Post-deploy (manual or scripted against prod/staging)**

1. Marketing page loads; launcher visible when env enabled
2. Open widget → `session/start` 200, welcome message
3. Ask pricing question → grounded answer with sources when KB matches
4. Say “workflow audit” → intake question appears
5. Send `hello` → conversational reply (not generic loop)
6. Kill switch: set `FIKIRI_SITE_BOT_ENABLED=0` → API returns disabled; widget shows fallback
7. Rate limit: burst test returns 429 (staging only)

---

## Testing strategy (Phase 5)

| Layer | What to add |
|-------|-------------|
| Unit | Session serialize/deserialize, TTL logic, rate limit key builder |
| Integration | Redis session round-trip, rate limit 429, disabled flag 503 |
| Scenario | No change to intelligence scenarios unless guard/session interaction breaks |
| Smoke | Production checklist above |

Target: **+8–12 focused tests**, not a duplicate of the 65 existing tests.

---

## Implementation order

```
5a (go-live blockers)
  1. Redis session store
  2. Rate limits
  3. FIKIRI_SITE_BOT_ENABLED + widget error state
  4. CORS/env doc + smoke checklist
  → Deploy marketing widget to production

5b (enable when ready)
  5. site_chat_* migration + persist flag
  6. Admin read endpoints + capability
  7. Retention cleanup job
  → Set FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS=1
```

---

## Files expected to change (implementation phase)

| File | Change |
|------|--------|
| `company_chatbot/session_store.py` | New — Redis backing |
| `company_chatbot/orchestrator.py` | Use session store, optional transcript hook |
| `company_chatbot/config.py` | New env flags |
| `routes/site_chatbot_api.py` | Rate limits, enabled check |
| `routes/admin_site_chat.py` or extend admin routes | Transcript read (5b) |
| `database_init.py` / migration | `site_chat_*` tables (5b) |
| `frontend/src/components/FikiriSiteChatWidget.tsx` | Disabled API UX |
| `docs/FIKIRI_SITE_BOT_PRODUCTION_SMOKE.md` | New |
| `tests/test_site_chatbot_*.py` | Session + rate limit tests |

**Do not touch:** `core/public_chatbot_api.py`, `PublicChatbotWidget.tsx`, `core/chatbot_conversation_store.py` (tenant path).

---

## Open questions (resolve before coding 5b)

1. **Who gets `site_chat.read_transcripts`?** Owner only, or owner + support role?
2. **PII in transcripts:** When intake captures email, is 90-day retention acceptable under current privacy policy?
3. **Page URL capture:** Should widget send `document.location.href` on session start for attribution?

Default answers if no objection: (1) owner + admin, (2) 90 days with hash-only IP/UA, (3) yes, optional field on session start.

---

## Phase 6 preview (not Phase 5)

- CRM lead write from completed intake
- Slack/email notify on handoff
- LLM polish after expanded scenario suite
- In-widget handoff form (`HANDOFF_PRIMARY_WIDGET`)

---

## Sign-off criteria for Phase 5 complete

- [ ] Redis-backed sessions in production
- [ ] Rate limits active on both site chat routes
- [ ] Backend kill switch tested
- [ ] CORS verified for production domain
- [ ] Smoke checklist executed on staging/production
- [ ] Backend + frontend test commands in this doc all green
- [ ] Transcript slice either shipped behind flag **or** explicitly deferred with written decision
