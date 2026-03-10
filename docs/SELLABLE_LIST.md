# Sellable List — What We Know Works

Single reference for **features and capabilities we know work**: implemented, covered by tests, and passing guardrails. Use for sales, support, and release notes.

## Definitions (do not skip)

- **WORKS (Tested):** Backend tests for that area pass + forbidden-patterns scan passes.
- **SELLABLE (Staging):** WORKS + required provider health present (keys/tokens) + readiness summary green.
- **PRODUCTION SELLABLE:** SELLABLE + monitoring/alerts enabled + (recommended) provider contract tests green.

This prevents “but it passed tests” arguments: tests alone = WORKS; staging-ready = SELLABLE; production-ready = PRODUCTION SELLABLE.

---

## Verify

**Local (WORKS):**

```bash
pytest -q tests -m "not contract and not integration"
python3 scripts/automation_readiness.py --summary
```

**Staging (SELLABLE) — contract tests (Gmail/Stripe sandbox):**

```bash
pytest -q tests/contract -m contract
```

See [TESTING.md](TESTING.md) and [AUTOMATION_READINESS.md](AUTOMATION_READINESS.md) for full gate.

---

## Provider requirements (quick matrix)

| Capability | OAuth tokens needed | Env keys needed | Notes |
|------------|---------------------|-----------------|-------|
| CRM only | ❌ | ❌ | No external provider required |
| Mailbox automation | ✅ Gmail/Outlook | ❌ | User must connect mailbox in-app |
| Public chatbot (LLM) | ❌ | ✅ OPENAI_API_KEY | |
| Chatbot + RAG | ❌ | ✅ OPENAI_API_KEY + PINECONE_API_KEY | vector_search flag |
| Stripe billing (basic) | ❌ | ✅ STRIPE_SECRET_KEY + STRIPE_WEBHOOK_SECRET | contract tests recommended |
| SMS workflows | ❌ | ✅ TWILIO_* | only if selling SMS |

---

## Known operational dependencies

Even when code passes and provider health is green, the following must be operational. Failure in any can move **WORKS → not SELLABLE** or **SELLABLE → not PRODUCTION SELLABLE**.

| Dependency | Required for |
|------------|--------------|
| **Database** reachable, migrations applied | All capabilities; CRM, auth, webhooks, billing state |
| **Redis** reachable (if queues/caching enabled) | Mailbox automation, rate limits, cache, job queues |
| **Background worker** process running (if using async jobs) | Gmail sync, scheduled workflows, cleanup jobs |
| **Outbound internet** access | Provider APIs (OpenAI, Pinecone, Gmail, Outlook, Stripe, Twilio) |
| **Correct domain + HTTPS** configured | OAuth callbacks (Gmail/Outlook), Stripe webhooks |

**Why this section:** Enterprise buyers ask *“What operational assumptions does your system make?”* This is the answer.

---

## 1. Lead capture → CRM

| What works | Evidence |
|------------|----------|
| Webhook intake (inbound leads) | `test_webhook_api.py`, `test_webhook_intake_service.py` |
| Lead/contact CRUD, pipeline, stages | `test_crm_service.py`, `test_crm_completion_api.py`, `test_business_routes.py` |
| CRM completion API (stage updates, merge) | `test_crm_completion_api.py` |
| Revenue flow: lead intake end-to-end | `test_revenue_lead_intake.py` |

**Customer requirement:** None (CRM-only works without external providers).

---

## 2. Inbox / email automation

| What works | Evidence |
|------------|----------|
| Email parsing, classification, actions | `test_email_parser.py`, `test_email_actions.py`, `test_email_pipeline.py`, `test_email_action_handlers.py` |
| Gmail client (auth, list, sync) | `test_gmail_client.py`, `test_gmail_sync_jobs.py`, `test_app_oauth.py` |
| Service manager, idempotency, safety | `test_email_service_manager.py`, `test_idempotency_manager.py`, `test_automation_safety.py` |
| Inbox routes (list, read, actions) | `test_inbox_routes.py` |
| Revenue flow: mailbox automation | `test_revenue_mailbox_automation.py` |

**Customer requirement:** User must connect Gmail/Outlook (OAuth) in-app; without tokens this remains WORKS but not SELLABLE.

---

## 3. Auth & security

| What works | Evidence |
|------------|----------|
| User auth, JWT, sessions | `test_user_auth.py`, `test_jwt_auth.py`, `test_secure_sessions.py`, `test_auth_routes.py` |
| OAuth token lifecycle | `test_oauth_token_manager.py`, `test_app_oauth.py` |
| API key management | `test_api_key_manager.py` |
| Rate limiting | `test_rate_limiter.py` |
| Revenue flow: billing + security | `test_revenue_billing_security.py` |

**Customer requirement:** None for auth/security itself; OAuth is for mailbox/calendar, not “login as a customer.”

---

## 4. Public API (chatbot & AI analysis)

| What works | Evidence |
|------------|----------|
| Public chatbot query | `test_public_chatbot_api.py` |
| AI analysis (contact/lead/business) | `test_ai_analysis_api.py` |
| Public endpoint auth + rate limits | `test_api_key_manager.py`, `test_public_chatbot_api.py` |
| Vector persistence + KB sync | `test_vector_persistence.py`, `test_kb_vector_sync.py` |
| Revenue flow: chatbot | `test_revenue_chatbot_flow.py` |

**Customer requirement:** OPENAI_API_KEY required. RAG requires PINECONE_API_KEY + vector_search enabled. See [PUBLIC_API_DOCUMENTATION.md](PUBLIC_API_DOCUMENTATION.md).

---

## 5. Billing (Stripe — basic subscription flow)

| What works | Evidence |
|------------|----------|
| Checkout session, customer creation | `test_billing_stripe.py`, `test_stripe_webhooks.py`, `test_billing_manager.py` |
| Webhook signature verification/handler | `test_stripe_webhooks.py` |
| Revenue flow: billing + security | `test_revenue_billing_security.py` |

**Customer requirement:** STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET.

**Note:** If relying on self-serve trials + complex lifecycle, add deeper subscription edge coverage (see [BACKEND_TEST_COVERAGE_GAP.md](BACKEND_TEST_COVERAGE_GAP.md)).

---

## 6. Workflows & appointments

| What works | Evidence |
|------------|----------|
| Workflow routes, followups, reminders | `test_workflow_routes.py`, `test_workflow_followups.py`, `test_appointment_reminders.py` |
| Workflow templates API/system | `test_workflow_templates_api.py`, `test_workflow_templates_system.py` |
| Appointments routes/service | `test_appointments_routes.py`, `test_appointments_service.py` |
| Automation engine | `test_automation_engine.py` |

**Customer requirement:** Gmail/Outlook for email workflows; Twilio only if selling SMS workflows.

---

## 7. Health, monitoring, and operations

| What works | Evidence |
|------------|----------|
| Health endpoint and status | `test_health_checks.py` |
| Monitoring API and routes | `test_monitoring_api.py`, `test_monitoring_routes.py` |
| Dashboard API (partial) | `test_dashboard_api.py` |

**Customer requirement:** None; DB and Redis (if used) must be up.

---

## 8. Supporting systems (tested, used by sellable features)

| What works | Evidence |
|------------|----------|
| LLM client, router, validators | `test_llm_client.py`, `test_llm_router.py`, `test_validators.py` |
| Feature flags, minimal config, error handling | `test_feature_flags.py`, `test_minimal_config.py`, `test_error_handling.py` |
| Integration framework | `test_integration_framework.py` |
| Redis (cache, queues) | `test_redis_modules.py` |
| Onboarding and user routes | `test_onboarding_routes.py`, `test_user_routes.py` |

---

## Not on the sellable list (partial or coming soon)

- **Analytics dashboard:** Partial; not all metrics guaranteed. See [COMING_SOON.md](COMING_SOON.md).
- **Integrations:** Gmail and Outlook are sellable; other providers (e.g. Notion) may be stubs. See [COMING_SOON.md](COMING_SOON.md).
- **Social login (GitHub):** Disabled in UI; “Coming soon.”
- **Self-serve trials (Stripe):** Basic flow tested; deeper subscription/billing_manager coverage is a known gap if you rely on it.

---

## One-line summary

**WORKS (tested):** Lead capture & CRM, inbox automation, auth & API keys, public chatbot & AI analysis, Stripe billing (basic), workflows & appointments, health/monitoring. **SELLABLE** requires provider health (matrix above); **PRODUCTION SELLABLE** adds monitoring/alerts and (recommended) contract tests. Run `scripts/automation_readiness.py --summary` and see [AUTOMATION_READINESS.md](AUTOMATION_READINESS.md).
