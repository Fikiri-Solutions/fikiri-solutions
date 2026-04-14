# Production release notes (pending deploy)

This document categorizes **current local changes** on `main` (not yet pushed) and records verification done before production.

**Last verification:** automated tests + frontend build (see §4).  
**Deploy recommendation:** ship **backend API and frontend together** so JWT refresh (`POST /api/auth/refresh` with body) and the client interceptor stay in sync.

---

## 1. Authentication & session (high impact)

| Area | Change | Key files |
|------|--------|-----------|
| **Refresh token API** | `POST /api/auth/refresh` accepts JSON `{"refresh_token":"..."}` when the access token is expired; legacy mode (`Authorization: Bearer <valid access>`) unchanged. | `routes/auth.py` |
| **SPA storage** | Persist `fikiri-refresh-token` on login/signup; clear with `fikiri-token` on logout. | `frontend/src/contexts/AuthContext.tsx` |
| **Automatic retry** | On `401`, single-flight refresh then one retry; skips auth endpoints to avoid loops; logo GET still avoids forced redirect when unauthenticated. | `frontend/src/services/apiClient.ts` |
| **Tests** | Body-based refresh covered. | `tests/test_auth_routes.py` |

**Post-deploy expectation:** Users with **only** an old `fikiri-token` and **no** `fikiri-refresh-token` should **log in once** to store the refresh token. After that, expired access tokens renew without 401 noise on assets like `/api/user/customization/logo`.

---

## 2. AI / email analysis (LLM pipeline)

| Area | Change | Key files |
|------|--------|-----------|
| **Output normalization** | Stronger JSON extraction/coercion before schema validation; relaxed validators where models return numbers/strings. | `core/ai/llm_router.py`, `core/ai/validators.py` |
| **Assistant** | Minor alignment with router behavior. | `email_automation/ai_assistant.py` |
| **Tests** | Router and validator tests updated. | `tests/test_llm_router.py`, `tests/test_validators.py` |

---

## 3. Email, Gmail sync & inbox UX

| Area | Change | Key files |
|------|--------|-----------|
| **Gmail list/detail** | Inbox-aligned queries (e.g. `in:inbox`), read/unread handling for live Gmail vs synced DB paths; related fixes. | `routes/business.py` |
| **Sync persistence** | Synced rows store read state from Gmail labels where applicable. | `email_automation/gmail_sync_jobs.py` |
| **Inbox UI** | Layout and behavior (list/detail/AI strip, `use_synced` behavior, refetch). | `frontend/src/pages/EmailInbox.tsx` |
| **Tests** | Business route tests updated. | `tests/test_business_routes.py` |

---

## 4. Platform & infrastructure (supporting)

| Area | Change | Key files |
|------|--------|-----------|
| **Database** | Schema/optimization adjustments tied to features above. | `core/database_optimization.py` |
| **OAuth tokens** | Token manager updates (Google/OAuth flows). | `core/oauth_token_manager.py` |
| **Onboarding jobs** | Job handling updates. | `core/onboarding_jobs.py` |
| **Redis** | Connection helper and queue tweaks. | `core/redis_connection_helper.py`, `core/redis_queues.py` |
| **Security** | Middleware/security adjustments. | `core/security.py` |
| **Reminders / follow-ups** | Small fixes. | `core/appointment_reminders.py`, `core/workflow_followups.py` |
| **Tests** | Redis module tests. | `tests/test_redis_modules.py` |
| **Frontend deps** | `frontend/package.json` (lockfile may need `npm install` in CI/deploy). | `frontend/package.json` |

---

## 5. Optional / not in this commit

The following are **optional** follow-ups (not required for main app deploy):

- `core/gmail_inline_images.py`, `tests/test_gmail_inline_images.py`

---

## 6. Verification log (pre-push)

| Check | Result |
|-------|--------|
| `pytest` (focused): `test_auth_routes`, `test_business_routes`, `test_llm_router`, `test_validators`, `test_redis_modules` | **168 passed** |
| `npm run build` (frontend) | **Success** |
| `tsc --noEmit` (frontend) | **Clean** (after refresh-token typings) |
| Flake8 on large legacy files (`routes/business.py`, `routes/auth.py`, `core/ai/llm_router.py`) | Many **pre-existing** style warnings (whitespace, E501, etc.); not introduced solely by this release. Run `black`/`ruff` in a dedicated cleanup PR if CI enforces strict flake8 on these paths. |

---

## 7. Pre-production checklist

1. [ ] Confirm **Render / hosting** deploy order: API + static frontend in one release or API first (body refresh is backward compatible; old clients keep failing refresh until updated).
2. [ ] **Environment:** `DATABASE_URL`, Redis, JWT secret, Gmail OAuth — unchanged assumptions unless noted in infra tickets.
3. [ ] **Smoke after deploy:** log in → open inbox → wait past access TTL (or force expired token) → confirm no persistent 401 on logo/customization; Gmail list still loads.
4. [ ] Decide whether to add **untracked** files (§5) to git or leave for a follow-up PR.
5. [ ] `git add` / `commit` / `push` (see §8).

---

## 8. Suggested git commands

```bash
# Review everything
git status
git diff --stat

# Stage tracked changes only (exclude untracked until you want them)
git add -u

# Or stage explicitly by area
git add routes/auth.py routes/business.py core/ frontend/src/ tests/ email_automation/

git commit -m "feat: JWT refresh for SPA, inbox/Gmail fixes, LLM validation hardening

- Auth: POST /api/auth/refresh accepts refresh_token body; client stores fikiri-refresh-token and retries 401s once
- Email: business routes + gmail sync + EmailInbox UX
- AI: llm_router/validators normalization and tests
- Infra: db, redis, oauth, onboarding, security touch-ups"

git push origin main
```

Adjust the commit message to match your team’s convention (e.g. conventional commits, internal ticket IDs).

---

## 9. Rollback

- **Backend:** redeploy previous API image/commit; clients that only use the new refresh body will fall back to “must log in again” if the old server rejects body refresh (legacy Bearer-only).
- **Frontend:** redeploy previous bundle; users keep refresh token in `localStorage` until cleared; no server-side migration required.
