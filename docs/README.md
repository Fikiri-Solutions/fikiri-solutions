# Fikiri Documentation

Quick reference for project documentation. Root-level: [`README.md`](../README.md), [`AGENTS.md`](../AGENTS.md), [`COORDINATION.md`](../COORDINATION.md) (Cursor + Codex), [`SIMPLICITY_RULE.md`](../SIMPLICITY_RULE.md), [`GOOGLE_APIS_REQUIRED.md`](../GOOGLE_APIS_REQUIRED.md), [`PINECONE_SETUP.md`](../PINECONE_SETUP.md).

**Multi-tool:** [`COORDINATION.md`](../COORDINATION.md) — shared rules for Cursor and Codex.

## Setup & Configuration

| Doc | Description |
|-----|-------------|
| [ENVIRONMENT_CONFIG.md](ENVIRONMENT_CONFIG.md) | Environment variables and config |
| [GOOGLE_OAUTH_SETUP.md](GOOGLE_OAUTH_SETUP.md) | Google OAuth scopes and setup |
| [gmail-api-scope-justification.md](gmail-api-scope-justification.md) | Gmail API scope justification (OAuth verification) |
| [OUTLOOK_SETUP.md](OUTLOOK_SETUP.md) | Outlook/Microsoft OAuth setup |
| [DOMAIN_SSL_SETUP.md](DOMAIN_SSL_SETUP.md) | Domain and SSL configuration |

## Architecture & Planning

| Doc | Description |
|-----|-------------|
| [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | System architecture overview |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Database schema reference |
| [CRITICAL_INTEGRATIONS_PLAN.md](CRITICAL_INTEGRATIONS_PLAN.md) | Integration priority matrix |

## Frontend

| Doc | Description |
|-----|-------------|
| [FRONTEND_UX_PATTERNS.md](FRONTEND_UX_PATTERNS.md) | Tooltips, modals, scroll—consistent UX patterns |
| [FRONTEND_AUTH_CHECKLIST.md](FRONTEND_AUTH_CHECKLIST.md) | Frontend auth checklist |

## Testing

| Doc | Description |
|-----|-------------|
| [TESTING.md](TESTING.md) | Pytest commands, sellability gate, stability run |
| [AUTOMATION_READINESS.md](AUTOMATION_READINESS.md) | Readiness script, SELLABLE requirements |
| [PUBLIC_API_TESTING.md](PUBLIC_API_TESTING.md) | Public API unit tests and smoke test |

## Implementation Reference

| Doc | Description |
|-----|-------------|
| [APPOINTMENT_SCHEDULING_IMPLEMENTATION.md](APPOINTMENT_SCHEDULING_IMPLEMENTATION.md) | Appointment scheduling schema and API |
| [INTEGRATION_FRAMEWORK_IMPLEMENTATION.md](INTEGRATION_FRAMEWORK_IMPLEMENTATION.md) | Integration framework details |
| [INTEGRATION_COMPLETE.md](INTEGRATION_COMPLETE.md) | Integration status and API contracts |
| [INTEGRATION_QUICK_START.md](INTEGRATION_QUICK_START.md) | Quick start for webhooks and SDK |
| [WEBHOOK_BUILDER_IMPLEMENTATION.md](WEBHOOK_BUILDER_IMPLEMENTATION.md) | Webhook payload builder |
| [BILLING_IMPROVEMENTS.md](BILLING_IMPROVEMENTS.md) | Billing system improvements |
| [PUBLIC_API_DOCUMENTATION.md](PUBLIC_API_DOCUMENTATION.md) | Public API reference (auth, endpoints) |
| [PUBLIC_API_IMPLEMENTATION.md](PUBLIC_API_IMPLEMENTATION.md) | Public API implementation summary |
| [CHATBOT_EMBED.md](CHATBOT_EMBED.md) | Website chatbot embed (public endpoint) |
| [SMS_CONSENT_TWILIO.md](SMS_CONSENT_TWILIO.md) | SMS express consent (CTIA/TCPA) and Twilio proof |

## Operations & Reliability

| Doc | Description |
|-----|-------------|
| [HEALTH_CHECK_GUIDE.md](HEALTH_CHECK_GUIDE.md) | Health check setup |
| [UPTIME_MONITORING_SETUP.md](UPTIME_MONITORING_SETUP.md) | Uptime monitoring |
| [monitoring-metrics.md](monitoring-metrics.md) | Prometheus metrics config |
| [DISASTER_RECOVERY_CHECKLIST.md](DISASTER_RECOVERY_CHECKLIST.md) | Disaster recovery procedures |
| [PRODUCTION_READINESS_CHECKLIST.md](PRODUCTION_READINESS_CHECKLIST.md) | Production deployment checklist |
| [FINANCIAL_MODEL_AND_RATE_LIMITING.md](FINANCIAL_MODEL_AND_RATE_LIMITING.md) | Pricing, cost, rate limiting, capacity |

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
| [CLIENT_ONBOARDING_GUIDE.md](CLIENT_ONBOARDING_GUIDE.md) | Client onboarding flow |

## Reference

| Doc | Description |
|-----|-------------|
| [COMING_SOON.md](COMING_SOON.md) | Features not guaranteed / coming soon (UI and backend) |
