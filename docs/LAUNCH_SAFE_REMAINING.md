# Launch-Safe 100%: Remaining External Validation

The remaining gap to **launch-safe 100%** is mostly **external dependency validation**: running the same quality gates with real OAuth, real Stripe, and real mail providers against a prod-like environment.

---

## 1. Gmail / Outlook connected-token integration

**Goal:** Run contract/integration scenarios with **real OAuth credentials** so token refresh and mailbox access are validated end-to-end.

### Gmail contract tests (existing)

Require sandbox OAuth creds. From repo root:

```bash
# Set one of:
# - GMAIL_CONTRACT_ACCESS_TOKEN (short-lived), or
# - GMAIL_OAUTH_CLIENT_ID + GMAIL_OAUTH_CLIENT_SECRET + GMAIL_REFRESH_TOKEN
#   (or GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_REFRESH_TOKEN)

pytest tests/contract/test_gmail_contract.py -v
```

Optional: `pip install requests` if not already in `requirements.txt`.

### Outlook

There is no dedicated Outlook contract test yet. To validate Outlook connected-token:

- **Manual:** Use the app’s Connect Outlook flow (Integrations or Onboarding), then run `python3 scripts/automation_readiness.py --summary` and confirm Outlook is reported connected.
- **Future:** Add `tests/contract/test_outlook_contract.py` (token refresh + list messages) similar to Gmail, gated by `@pytest.mark.contract` and Outlook env vars.

### Getting tokens into the app

See [CONNECT_GMAIL_OUTLOOK.md](CONNECT_GMAIL_OUTLOOK.md): connect Gmail/Outlook in the Fikiri UI; tokens are stored in DB. Re-run `automation_readiness.py --summary` to confirm “gmail: connected” / “outlook: connected”.

---

## 2. E2E onboarding spec (signup fixed)

**Goal:** Run **e2e.onboarding.spec.ts** now that signup is fixed, as part of the full launch readiness suite.

### Run locally (backend + frontend up)

```bash
# Terminal 1: backend
python3 app.py

# Terminal 2: frontend
cd frontend && npm run dev

# Terminal 3: E2E (includes onboarding)
cd frontend
npx playwright test tests/e2e.onboarding.spec.ts
```

### Run as part of full launch readiness

From repo root, E2E is included when `RUN_E2E_TESTS=1`:

```bash
RUN_E2E_TESTS=1 ./scripts/run_launch_readiness.sh
```

That runs `e2e.auth.spec.ts`, `e2e.onboarding.spec.ts`, and `e2e.automations.spec.ts`. Ensure Playwright auth env is set (e.g. `TEST_USER_EMAIL`, `TEST_USER_PASSWORD`) if the specs need a logged-in user; see [TESTING.md](TESTING.md) § 3.1.

---

## 3. Full readiness suite against staging / prod-like env

**Goal:** Run the **same full readiness suite** (backend critical-path, integration, E2E) against a **staging or prod-like** environment with **real Stripe** and **real mail providers** (Gmail/Outlook).

### What to run

- Backend critical-path tests (auth, business routes, billing guardrails, automation safety/queue).
- Integration tests (auth/CRM smoke, queue jobs, automation launch).
- E2E (auth, onboarding, automations).

### Option A: Backend + integration against staging URL

Point pytest at the staging backend and use a real test user:

```bash
export INTEGRATION_BACKEND_URL="https://your-staging-api.example.com"
export INTEGRATION_LOGIN_EMAIL="your-staging-test-user@example.com"
export INTEGRATION_LOGIN_PASSWORD="your-staging-test-password"

RUN_INTEGRATION_TESTS=1 ./scripts/run_launch_readiness.sh
```

Staging backend must have:

- Stripe: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and (for contract) `STRIPE_TEST_PRICE_ID` set to real test-mode values.
- Gmail/Outlook: tokens in DB (via Connect in the app on staging) or env used by contract tests if you run them separately against staging.

### Option B: E2E against staging frontend + backend

Run Playwright against the staging frontend URL (and ensure the app uses the staging API):

```bash
# In frontend, set baseURL to staging (e.g. in playwright.config or env)
# Then run E2E with that config
cd frontend
BASE_URL=https://your-staging-app.example.com npx playwright test tests/e2e.auth.spec.ts tests/e2e.onboarding.spec.ts tests/e2e.automations.spec.ts
```

Use test credentials that exist on staging.

### Option C: One-command “staging readiness” script (optional)

You can add a wrapper script, e.g. `scripts/run_staging_readiness.sh`, that sets `INTEGRATION_BACKEND_URL`, `RUN_INTEGRATION_TESTS=1`, `RUN_E2E_TESTS=1`, and (if applicable) `BASE_URL` for Playwright, then calls `./scripts/run_launch_readiness.sh`. That keeps “full readiness against staging” a single command.

---

## Checklist summary

| Gate | Command / action | Env / notes |
|------|------------------|-------------|
| Gmail connected-token | `pytest tests/contract/test_gmail_contract.py -v` | Gmail OAuth env (see above) |
| Outlook connected-token | Connect in app → `automation_readiness.py --summary` | Optional: add Outlook contract test |
| E2E onboarding | `npx playwright test tests/e2e.onboarding.spec.ts` or full `run_launch_readiness.sh` with `RUN_E2E_TESTS=1` | Backend + frontend running; Playwright auth if needed |
| Full readiness on staging | `RUN_INTEGRATION_TESTS=1 [RUN_E2E_TESTS=1] INTEGRATION_BACKEND_URL=<staging> ./scripts/run_launch_readiness.sh` (+ E2E against staging frontend if desired) | Staging has real Stripe (test mode) + mail provider tokens |

Once these are run and green (and any new contract/E2E tests added as above), the stack is at **launch-safe 100%** from an external-dependency validation perspective.
