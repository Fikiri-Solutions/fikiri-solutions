# E2E Test Plan — Before Manual QA

Run these E2E tests before manual testing or handing off to QA. They use Playwright against the running app (frontend + backend).

## Quick run

```bash
# From repo root: start backend (port 5000) and frontend (5174) first, or use webServer in config
cd frontend
npx playwright test
```

With auth env (see [Auth setup](#auth-setup)):

```bash
cd frontend
TEST_USER_EMAIL=... TEST_USER_PASSWORD=... npx playwright test
```

Run only critical paths (fast smoke):

```bash
cd frontend
npx playwright test tests/e2e.critical-paths.spec.ts tests/e2e.crm.spec.ts tests/e2e.crm-trace.spec.ts tests/e2e.auth.spec.ts --project=e2e
```

Run public pages only (no auth required):

```bash
cd frontend
npx playwright test tests/e2e.critical-paths.spec.ts --grep "Public pages"
```

---

## What you already have

| Spec | Coverage |
|------|----------|
| **e2e.auth.spec.ts** | Login, redirect when unauthenticated, login error messages, rate limiting, onboarding steps, skip onboarding, cookies, CORS, password manager |
| **e2e.onboarding.spec.ts** | Signup→dashboard, OAuth placeholder, step progression, validation, error handling, progress persistence |
| **e2e.automations.spec.ts** | Automations dashboard, queue health, capabilities, run preset test, activate preset (with API mocks) |
| **e2e.crm-trace.spec.ts** | CRM **View trace** modal: mocked `GET /crm/leads`, `GET /crm/leads/:id/events`, `GET /debug/correlation/:id`; asserts correlation ID, stitched timeline, Escape closes |

---

## Recommended E2E to run before manual QA

### 1. Critical paths (smoke)

- **Dashboard loads** — After login, `/dashboard` loads and shows metrics or placeholder content (no 500, no blank screen).
- **CRM page loads** — `/crm` loads and shows pipeline or empty state (no 500).
- **Automations page loads** — `/automations` loads and shows presets or queue health.
- **Billing page loads** — `/billing` or pricing loads without error (for logged-in or public).
- **Public pages** — `/pricing`, `/terms`, `/privacy`, `/contact` load and show content.

**Spec:** `tests/e2e.critical-paths.spec.ts` (see below).

### 2. CRM flows

- **CRM list and pipeline** — GET leads, pipeline columns render, empty state or at least one lead.
- **Add lead (optional)** — Submit form or use “Add lead” if present; confirm lead appears in list or success message.
- **Pipeline stage change (optional)** — Drag or change stage; confirm update (if implemented in UI).

**Spec:** `tests/e2e.crm.spec.ts`.

- **View trace (correlation)** — Mocked API; opens modal from **View trace**, loads stitched timeline. **Spec:** `tests/e2e.crm-trace.spec.ts` (`--project=e2e`).

### 3. Auth and signup

- **Signup → login → dashboard** — Full flow with a new email; confirm redirect to dashboard or onboarding.
- **Logout** — Logout clears session and redirects to login or landing.

Covered in `e2e.auth.spec.ts` and `e2e.onboarding.spec.ts`; ensure auth setup uses a real or stable test user.

### 4. Integrations and settings (light)

- **Integrations page** — `/integrations` or Gmail/Outlook connect page loads; no need to complete OAuth in E2E unless you have a dedicated test account.
- **Profile/settings** — Settings or profile page loads (if present).

### 5. Staging / API-backed E2E (optional)

- **Lead capture → CRM** — Use `scripts/validate_staging_e2e.py` with real staging URL and API key; confirms webhook → CRM → logs without browser.
- **Playwright against staging** — Point `APP_URL` and backend to staging; run the same specs to catch env-specific issues.

---

## Auth setup

E2E projects use `playwright/.auth/state.json` from `tests/auth.setup.ts`. Set:

- `TEST_USER_EMAIL` — existing user for “e2e” and “admin-e2e” projects.
- `TEST_USER_PASSWORD` — password for that user.

**Do not use placeholder values** (e.g. `your@test.user` / `yourpass`). If those are set in your env, unset them so the setup uses the defaults (`test@example.com` / `TestPassword123!`). With defaults, the setup will try to create the user via signup on first run if login returns 401.

For **onboarding-e2e** and **new-user-state**, setup may create or use a different user; check `auth.setup.ts` for variables.

**Signup rate limit (429):** The backend limits signups to **3 per hour per IP** in production. E2E setup triggers signup in two places: (1) `authenticate-new-user` creates a new user every run (`test-${timestamp}@example.test` — not `@example.com`, which has Null MX and causes Gmail bounces), and (2) `authenticate` may create the default user (`test@example.com`) if login returns 401. So 2–3 runs per hour can hit the limit. **In development** (`FLASK_ENV=development`) or test mode (`FIKIRI_TEST_MODE=1`), the signup limit is bypassed so E2E can run repeatedly. If you still see 429, start the backend with `FLASK_ENV=development` or `FIKIRI_TEST_MODE=1`.

---

## Suggested order before QA

1. **Backend unit/route** — `pytest tests -m "not contract and not integration" -q`
2. **Provider readiness** — `python3 scripts/run_provider_readiness.py` (and `--run-contract-tests` if providers configured)
3. **E2E critical + auth + CRM** — `npx playwright test tests/e2e.auth.spec.ts tests/e2e.critical-paths.spec.ts tests/e2e.crm.spec.ts`
4. **E2E full** — `npx playwright test`
5. **Staging E2E (if staging exists)** — `python3 scripts/validate_staging_e2e.py` with staging env
6. **Manual QA** — Real user flows, cross-browser, mobile, and edge cases

---

## New specs added

- **e2e.critical-paths.spec.ts** — Dashboard, CRM, Automations, Billing, public pages load (smoke).
- **e2e.crm.spec.ts** — CRM list, pipeline, optional add-lead flow.

These depend on the same auth state as other e2e tests (`storageState: 'playwright/.auth/state.json'`).

---

## Other E2E you can add later

- **Mobile viewport** — Same specs with `--project=mobile-e2e` (already in config) or resize to 375px to catch layout/breakpoint issues.
- **Cross-browser** — `--project=firefox` and `--project=safari` (config already has these) for browser-specific bugs.
- **Signup → first lead** — Full flow: signup, login, go to CRM, create one lead via UI (or trigger webhook via API), confirm it appears.
- **Inbox page** — `/inbox` loads and shows empty state or emails (if Gmail/Outlook connected).
- **Chatbot builder** — `/ai/chatbot-builder` loads without error.
- **Accessibility** — `@axe-core/playwright` or Playwright’s `expect(page).toHaveAccessibleName(...)` for key flows.
- **Visual regression** — `expect(await page.screenshot()).toMatchSnapshot()` for critical pages (optional, needs baseline).
