# Backend Test Coverage Gap

Short reference for test counts, how to run the suite, the sellability gate, and highest-value remaining gaps.

---

## Test count (current)

| Scope | Test functions | Notes |
|-------|----------------|--------|
| **All** | ~645 | Unit + route + contract + integration |
| **Backend** (excl. contract & integration) | ~612 | Use for daily runs and sellability gate (A) |

*Count: `grep -r "def test_" tests --include="*.py" \| wc -l`*

---

## How to run (pytest, not unittest)

The repo is pytest-shaped (fixtures, markers). Use pytest so the full suite is exercised.

| Use case | Command |
|----------|---------|
| **Fast local (daily)** | `pytest -q tests -m "not contract and not integration"` |
| **Full backend, useful output** | `pytest tests -m "not contract and not integration" -q --disable-warnings --maxfail=1` |
| **Full everything (release)** | `pytest -q` |
| **Stability gate (3/3)** | `for i in 1 2 3; do pytest -q tests -m "not contract and not integration" \|\| break; done` |

See **docs/TESTING.md** for full testing and sellability gate.

---

## Sellability gate (3 parts)

**SELLABLE** for a service only when all three pass:

- **A) Revenue-flow tests pass** — Backend unit/route tests green (`pytest -m "not contract and not integration"` or revenue subset).
- **B) Forbidden-patterns scan** — No direct OpenAI outside `core/ai`; no `print()` in prod paths; no hardcoded backend URLs in frontend.
- **C) Provider health** — Gmail/Outlook tokens (if mailbox); OpenAI/Pinecone (if chatbot); Stripe keys + webhook (if billing); Twilio (if SMS).

Run the gate:

```bash
python3 scripts/automation_readiness.py --summary
```

With full backend suite for (A):

```bash
python3 scripts/automation_readiness.py --full-backend --summary
```

---

## What’s actually left (high-value gaps)

From the coverage report, the highest-value **missing or thin** tests:

| Area | Priority | Notes |
|------|----------|--------|
| **core/billing_manager.py** | High if self-serve trials | Subscription lifecycle, plan enforcement edge cases. |
| **core/stripe_webhooks.py** | High if self-serve trials | Payload handling beyond basic handler test. |
| **analytics/dashboard_api.py** | Medium | Metrics endpoints beyond debug. |
| **services/business_operations.py** | Medium | Dedicated unit tests (today only route coverage). |
| **Core 16 domain/features** (remaining modules) | Lower | Unless sold explicitly (see TESTING.md). |

If you sell self-serve trials, Stripe webhooks + billing_manager tests move up the list.

---

## Priorities (outcome-driven)

1. **Lead capture → CRM** — webhook_api, webhook_intake_service, crm completion (covered).
2. **Inbox automation** — parser, pipeline, actions, service_manager, Gmail client (covered).
3. **CRM & pipeline** — business routes, automation_engine (covered); business_operations (partial).
4. **Billing + Stripe** — basic covered; deeper payload + billing_manager (gap).
5. **Auth / rate limiting** — covered.
6. **Analytics / monitoring** — monitoring_api covered; full dashboard (partial).

Use **docs/TESTING.md** for full testing flow and **scripts/automation_readiness.py** for the sellability gate.

---

## Background Jobs Status (Feb 2026)

**Current State:**
- ✅ Gmail sync job queuing moved to RQ (primary path)
- ⚠️ Threading fallback still exists when Redis unavailable (`routes/business.py` lines 307-322)
- ⚠️ `enhanced_crm_service.sync_gmail_leads(user_id)` runs synchronously after queueing (`routes/business.py` line 331)

**Note**: The threading fallback is intentional for resilience, but `sync_gmail_leads()` should also be moved to RQ for full async processing. See `docs/BACKGROUND_JOBS_ARCHITECTURE.md` for details.
