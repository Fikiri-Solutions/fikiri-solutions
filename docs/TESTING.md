# Testing & Sellability Gate

How to run tests the right way (pytest, not one-off unittest) and how sellability is determined.

---

## 1. Running the suite (pytest)

The repo is **pytest-shaped** (fixtures, `caplog`, markers). Use pytest so the full suite is exercised; `unittest` on a single file can pass while the rest of the suite is broken.

### Fast local (backend only, most useful daily)

```bash
pytest -q tests -m "not contract and not integration"
```

### Full backend with useful output

```bash
pytest tests -m "not contract and not integration" -q --disable-warnings --maxfail=1
```

### Full everything (when close to release)

```bash
pytest -q
```

### Proof of stability (readiness gate “3/3”)

```bash
for i in 1 2 3; do pytest -q tests -m "not contract and not integration" || break; done
```

**Markers:** `contract` = real provider contract tests (sandbox creds). `integration` = staging/DB/Redis. Excluding them gives the **backend unit + route** set that should be fast and reliable locally.

---

## 2. Sellability gate (3 parts)

Tests alone are not enough to sell. **SELLABLE** requires all three per service:

| Part | What it checks |
|------|----------------|
| **A) Revenue-flow tests pass** | Relevant unit/route tests green (backend suite with `not contract and not integration`, or subset). |
| **B) Forbidden-patterns scan** | No direct OpenAI outside `core/ai`; no `print()` in prod paths; no hardcoded backend URLs in frontend. |
| **C) Provider health** | For services that need it: Gmail/Outlook tokens exist + refresh works; OpenAI/Pinecone keys if chatbot is sold; Stripe keys + webhook secret if billing is live; Twilio if SMS workflows are sold. |

**Result:** A service is **SELLABLE** only when A + B + C are true for that service. Otherwise **BETA** (e.g. “BETA until tokens + contract tests”) or **NOT READY**.

---

## 3. Readiness run (one command)

```bash
python3 scripts/automation_readiness.py
```

With human-readable summary:

```bash
python3 scripts/automation_readiness.py --summary
```

This runs:

- **(A)** Pytest: `tests -m "not contract and not integration"` (or revenue subset with `--revenue-only`).
- **(B)** Forbidden-patterns scan (OpenAI, prints, frontend URLs).
- **(C)** Provider health (env + optional DB tokens).
- **(D)** AI launch-gate eval for inbound email triage (`scripts/run_email_triage_eval.py`) for AI services.

Then prints per service:

- ✅ / ❌ tests pass  
- ✅ / ❌ guardrails pass  
- ✅ / ❌ provider configured (or N/A)  
- ✅ / ⏭ contract tests (or skipped)  
- ✅ / ❌ observability (logs/metrics hooks)  

And a **sellability table**, e.g.:

- CRM = SELLABLE  
- Mailbox automation = BETA until tokens + contract tests  
- Chatbot = BETA until OpenAI/Pinecone configured and contract tests  
- Billing = BETA until Stripe keys + webhook contract tests  

Exit codes: `0` = all SELLABLE; `1` = at least one BETA; `2` = at least one NOT READY.

Run AI gate directly:

```bash
python3 scripts/run_email_triage_eval.py
```

---

## 3.1 Launch readiness run (integration + E2E)

For launch prep, run the dedicated script from repo root:

```bash
./scripts/run_launch_readiness.sh
```

What it executes:

- Backend critical-path tests (auth/routes/billing guardrails/automation queue+safety)
- Integration suite (when `RUN_INTEGRATION_TESTS=1`)
- Playwright E2E suite (when `RUN_E2E_TESTS=1`)

Environment flags:

- `RUN_INTEGRATION_TESTS=1` requires:
  - `INTEGRATION_BACKEND_URL`
  - `INTEGRATION_LOGIN_EMAIL`
  - `INTEGRATION_LOGIN_PASSWORD`
- `RUN_E2E_TESTS=1` requires frontend + backend running and Playwright auth setup credentials (`TEST_USER_EMAIL`, `TEST_USER_PASSWORD`, etc.)

Examples:

```bash
# Backend only (fast sanity)
./scripts/run_launch_readiness.sh

# Backend + integration
RUN_INTEGRATION_TESTS=1 INTEGRATION_BACKEND_URL=http://localhost:5000 \
INTEGRATION_LOGIN_EMAIL=test@example.com INTEGRATION_LOGIN_PASSWORD=TestPassword123! \
./scripts/run_launch_readiness.sh

# Full launch suite
RUN_INTEGRATION_TESTS=1 RUN_E2E_TESTS=1 \
INTEGRATION_BACKEND_URL=http://localhost:5000 \
INTEGRATION_LOGIN_EMAIL=test@example.com INTEGRATION_LOGIN_PASSWORD=TestPassword123! \
./scripts/run_launch_readiness.sh
```

**E2E (Playwright) note:** In specs that mock API routes (e.g. `frontend/tests/e2e.automations.spec.ts`), prefer asserting on **real outbound requests** (e.g. `page.waitForRequest(...)`) rather than counting mock-handler invocations. When multiple handlers can fulfill the same URL, handler counters may stay 0 and cause flaky failures; waiting for the actual request the browser sends is more reliable.

**CI/CD:** The main gate runs backend unit tests with `pytest tests/ -m "not contract and not integration"` and frontend lint + unit + build. Smoke test runs on `main` only. See [docs/CI_CD_STRATEGY.md](CI_CD_STRATEGY.md) for pipeline structure and how to keep local and CI in sync.

**Launch-safe 100%:** Remaining work is external dependency validation (Gmail/Outlook contract tests with real OAuth, E2E onboarding, full readiness suite against staging with real Stripe + mail). See [docs/LAUNCH_SAFE_REMAINING.md](LAUNCH_SAFE_REMAINING.md) for commands and env.

---

## 4. What’s left (high-value test gaps)

From the coverage report, the highest-value remaining tests if you want to tighten:

| Area | Priority | Notes |
|------|----------|--------|
| `core/billing_manager.py` | High if selling self-serve trials | Subscription lifecycle, plan enforcement edge cases. |
| `core/stripe_webhooks.py` | High if selling self-serve trials | Payload handling beyond the basic handler test. |
| `analytics/dashboard_api.py` | Medium | Metrics endpoints beyond debug. |
| `services/business_operations.py` | Medium | Dedicated unit tests (today only route coverage). |
| Core 16 domain/features (remaining modules) | Lower | Unless you sell those features explicitly. |

See `docs/BACKEND_TEST_COVERAGE_GAP.md` for the full gap list and priorities.
