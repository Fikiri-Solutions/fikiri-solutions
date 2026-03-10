# Launch Test Checklist

Minimum bar before launch: run the sellability gate and backend test suite, then (if selling provider-dependent features) run contract tests with sandbox creds.

---

## 1. Run the readiness gate (launch bar)

```bash
python3 scripts/automation_readiness.py --summary
```

**With full backend suite for (A):**

```bash
python3 scripts/automation_readiness.py --full-backend --summary
```

**What it checks:**

- **A) Revenue-flow tests** — Backend unit/route tests pass.
- **B) Guardrails** — No forbidden patterns (e.g. `print()` in prod paths, direct OpenAI outside `core/ai`, hardcoded backend URLs in frontend).
- **C) Provider health** — Gmail/Outlook (mailbox), OpenAI/Pinecone (chatbot), Stripe (billing), Twilio (SMS) as configured.

Services are **SELLABLE** only when all three pass for that service. Fix guardrails (e.g. remove or gate `print()` in examples) and configure providers (env vars, webhook secret for Stripe) as needed.

---

## 2. Run full backend tests (non-contract, non-integration)

```bash
python3 -m pytest -q tests -m "not contract and not integration"
```

Use this for daily runs and as the main “backend green” signal. For more verbose output:

```bash
python3 -m pytest tests -m "not contract and not integration" -q --disable-warnings --maxfail=1
```

---

## 3. Contract tests (if selling provider-dependent features)

Run with **sandbox/test credentials** (e.g. Stripe test keys, Gmail test account):

```bash
python3 -m pytest -q tests -m "contract"
```

Only run when the corresponding provider env vars are set; otherwise tests may be skipped.

---

## 4. High-value test gaps (addressed)

Targeted tests were added for launch-critical areas (see **BACKEND_TEST_COVERAGE_GAP.md**):

| Area | Priority | What was added |
|------|----------|----------------|
| **dashboard_api.py** | Medium | Metrics response shape (`ai.total`), DB error handling, timeseries `user_id`/`period` params. |
| **billing_manager.py** | High if billing live | Within-limits at boundary, `get_tier_limits`, checkout when Stripe unavailable, `cancel_subscription` (at period end). |
| **stripe_webhooks.py** | High if billing live | `handle_event` with `None`/empty, `handle_subscription_updated`, `verify_webhook_signature` when Stripe unavailable. |
| **business_operations.py** | Medium | Already had solid unit coverage; route coverage present. |

---

## 5. Other checks before launch (recommended)

- **Integration tests** — Run against staging DB/Redis if you rely on background jobs and queues:
  ```bash
  python3 -m pytest -q tests -m "integration"
  ```
- **Smoke test** — Manually or via E2E: auth → lead capture → CRM → automation on staging.
- **Provider health** — Confirm tokens/keys for Gmail, Outlook, Stripe, OpenAI, Pinecone (and Twilio if SMS is in scope) in the environment you’re launching.

---

## Quick reference

| Goal | Command |
|------|--------|
| Launch gate (summary) | `python3 scripts/automation_readiness.py --summary` |
| Launch gate + full backend | `python3 scripts/automation_readiness.py --full-backend --summary` |
| Backend tests (no contract/integration) | `python3 -m pytest -q tests -m "not contract and not integration"` |
| Contract tests (sandbox creds) | `python3 -m pytest -q tests -m "contract"` |
| Stability (3/3) | `for i in 1 2 3; do python3 -m pytest -q tests -m "not contract and not integration" \|\| break; done` |

See **TESTING.md** and **BACKEND_TEST_COVERAGE_GAP.md** for full testing flow and coverage notes.
