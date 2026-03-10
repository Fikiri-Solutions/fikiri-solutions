# Fikiri Documentation

Quick reference for project documentation. Root-level docs: [`COMPLETE_CODEBASE_WALKTHROUGH.md`](../COMPLETE_CODEBASE_WALKTHROUGH.md), [`SIMPLICITY_RULE.md`](../SIMPLICITY_RULE.md), [`GOOGLE_APIS_REQUIRED.md`](../GOOGLE_APIS_REQUIRED.md), [`PINECONE_SETUP.md`](../PINECONE_SETUP.md), [`COORDINATION.md`](../COORDINATION.md) (Cursor + Codex).

**Multi-tool:** [`COORDINATION.md`](../COORDINATION.md) — shared rules for Cursor and Codex working in unison.

## Setup & Configuration

| Doc | Description |
|-----|-------------|
| [ENVIRONMENT_CONFIG.md](ENVIRONMENT_CONFIG.md) | Environment variables and config |
| [GOOGLE_OAUTH_SETUP.md](GOOGLE_OAUTH_SETUP.md) | Google OAuth scopes and setup |
| [gmail-api-scope-justification.md](gmail-api-scope-justification.md) | Gmail API scope justification (OAuth verification) |
| [gmail-api-demo-script.md](gmail-api-demo-script.md) | Gmail API demo video script (OAuth verification) |
| [OUTLOOK_SETUP.md](OUTLOOK_SETUP.md) | Outlook/Microsoft OAuth setup |
| [YAHOO_INTEGRATION.md](YAHOO_INTEGRATION.md) | Yahoo Mail integration guide |
| [YAHOO_ACCESS_FORM_RESPONSES.md](YAHOO_ACCESS_FORM_RESPONSES.md) | Yahoo access request form responses |
| [DOMAIN_SSL_SETUP.md](DOMAIN_SSL_SETUP.md) | Domain and SSL configuration |

## Architecture & Planning

| Doc | Description |
|-----|-------------|
| [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | System architecture overview |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Database schema reference |
| [DEPENDENCY_GRAPH.md](DEPENDENCY_GRAPH.md) | Dependency relationships |
| [COMPLETE_BUSINESS_PLATFORM.md](COMPLETE_BUSINESS_PLATFORM.md) | Business platform feature goals |
| [FLEXIBLE_PLATFORM_APPROACH.md](FLEXIBLE_PLATFORM_APPROACH.md) | Flexible platform philosophy |
| [AI_GUIDED_PLATFORM.md](AI_GUIDED_PLATFORM.md) | AI-guided configuration approach |
| [INDUSTRY_SOLUTIONS_DELIVERY_PLAN_V2.md](INDUSTRY_SOLUTIONS_DELIVERY_PLAN_V2.md) | Industry packs architecture |
| [FOUNDER_ANALYSIS_INDUSTRY_PLAN.md](FOUNDER_ANALYSIS_INDUSTRY_PLAN.md) | Founder analysis and concerns |
| [CRITICAL_INTEGRATIONS_PLAN.md](CRITICAL_INTEGRATIONS_PLAN.md) | Integration priority matrix |
| [MOBILE_AND_INTEGRATION_STRATEGY.md](MOBILE_AND_INTEGRATION_STRATEGY.md) | Mobile and integration strategy |

## Frontend

| Doc | Description |
|-----|-------------|
| [FRONTEND_UX_PATTERNS.md](FRONTEND_UX_PATTERNS.md) | Tooltips, modals, scroll—consistent UX patterns |
| [FRONTEND_AUTH_CHECKLIST.md](FRONTEND_AUTH_CHECKLIST.md) | Frontend auth checklist |

## Testing

| Doc | Description |
|-----|-------------|
| [TESTING.md](TESTING.md) | Pytest commands, sellability gate, stability run |
| [BACKEND_TEST_COVERAGE_GAP.md](BACKEND_TEST_COVERAGE_GAP.md) | Test counts, gaps, priorities |
| [AUTOMATION_READINESS.md](AUTOMATION_READINESS.md) | Readiness script, SELLABLE requirements |
| [PROVIDER_CONTRACT_TESTS.md](PROVIDER_CONTRACT_TESTS.md) | Gmail/Stripe contract checks (sandbox) |
| [PUBLIC_API_TESTING.md](PUBLIC_API_TESTING.md) | Public API unit tests and smoke test |

## Implementation Reference

| Doc | Description |
|-----|-------------|
| [APPOINTMENT_SCHEDULING_IMPLEMENTATION.md](APPOINTMENT_SCHEDULING_IMPLEMENTATION.md) | Appointment scheduling schema and API |
| [INTEGRATION_FRAMEWORK_IMPLEMENTATION.md](INTEGRATION_FRAMEWORK_IMPLEMENTATION.md) | Integration framework details |
| [INTEGRATION_STATUS.md](INTEGRATION_STATUS.md) | Current integration status |
| [WEBHOOK_BUILDER_IMPLEMENTATION.md](WEBHOOK_BUILDER_IMPLEMENTATION.md) | Webhook payload builder |
| [BILLING_IMPROVEMENTS.md](BILLING_IMPROVEMENTS.md) | Billing system improvements |
| [PUBLIC_API_DOCUMENTATION.md](PUBLIC_API_DOCUMENTATION.md) | Public API reference (auth, endpoints) |
| [PUBLIC_API_IMPLEMENTATION.md](PUBLIC_API_IMPLEMENTATION.md) | Public API implementation summary |
| [CHATBOT_EMBED.md](CHATBOT_EMBED.md) | Website chatbot embed (public endpoint) |
| [CHATBOT_EVAL.md](CHATBOT_EVAL.md) | Chatbot eval: build sets, run eval, report location |
| [CHATBOT_FAQ_AUDIT.md](CHATBOT_FAQ_AUDIT.md) | Audit of all FAQ/chatbot code (APIs, scripts, feedback, eval) |
| [SMS_CONSENT_TWILIO.md](SMS_CONSENT_TWILIO.md) | SMS express consent (CTIA/TCPA) and Twilio proof for use case 30446 |

## Operations & Reliability

| Doc | Description |
|-----|-------------|
| [HEALTH_CHECK_GUIDE.md](HEALTH_CHECK_GUIDE.md) | Health check setup |
| [UPTIME_MONITORING_SETUP.md](UPTIME_MONITORING_SETUP.md) | Uptime monitoring |
| [monitoring-metrics.md](monitoring-metrics.md) | Prometheus metrics config |
| [DISASTER_RECOVERY_CHECKLIST.md](DISASTER_RECOVERY_CHECKLIST.md) | Disaster recovery procedures |
| [PRODUCTION_READINESS_CHECKLIST.md](PRODUCTION_READINESS_CHECKLIST.md) | Production deployment checklist |

## Security & Debugging

| Doc | Description |
|-----|-------------|
| [SECURITY_ASSESSMENT.md](SECURITY_ASSESSMENT.md) | Security assessment report |
| [AUTHENTICATION_DEBUG_GUIDE.md](AUTHENTICATION_DEBUG_GUIDE.md) | Auth debugging guide |
| [TROUBLESHOOTING_GUIDE.md](TROUBLESHOOTING_GUIDE.md) | General troubleshooting |

## Technical Deep Dives

| Doc | Description |
|-----|-------------|
| [CRUD_RAG_ARCHITECTURE.md](CRUD_RAG_ARCHITECTURE.md) | CRUD, RAG flow, identity/merge policy |
| [MUTEX_CONTENTION_MITIGATION.md](MUTEX_CONTENTION_MITIGATION.md) | Mutex contention fixes |
| [RULEPACK_AUDIT.md](RULEPACK_AUDIT.md) | Rulepack audit |
| [CLIENT_ONBOARDING_GUIDE.md](CLIENT_ONBOARDING_GUIDE.md) | Client onboarding flow |

## Reference

| Doc | Description |
|-----|-------------|
| [SELLABLE_LIST.md](SELLABLE_LIST.md) | What we know works — sellable features and test evidence |
| [COMING_SOON.md](COMING_SOON.md) | Features not guaranteed / coming soon (UI and backend) |
