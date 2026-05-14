# Fikiri Documentation

Quick reference for project documentation. Repo root (tooling / onboarding): [`README.md`](../README.md), [`AGENTS.md`](../AGENTS.md), [`COORDINATION.md`](../COORDINATION.md) (Cursor + Codex), [`SIMPLICITY_RULE.md`](../SIMPLICITY_RULE.md).

**Multi-tool:** [`COORDINATION.md`](../COORDINATION.md) — shared rules for Cursor and Codex.

**Business / GTM playbooks** (consultation, intake, pricing copy) live under [`docs/archive/business/`](archive/business/README.md), not in the tables below.

## Setup & Configuration

| Doc | Description |
|-----|-------------|
| [ENVIRONMENT_CONFIG.md](ENVIRONMENT_CONFIG.md) | Environment variables and config |
| [GOOGLE_OAUTH_SETUP.md](GOOGLE_OAUTH_SETUP.md) | Google OAuth scopes and setup |
| [gmail-api-scope-justification.md](gmail-api-scope-justification.md) | Gmail API scope justification (OAuth verification) |
| [OUTLOOK_SETUP.md](OUTLOOK_SETUP.md) | Outlook/Microsoft OAuth setup |
| [DOMAIN_SSL_SETUP.md](DOMAIN_SSL_SETUP.md) | Domain and SSL configuration |
| [DEV_SMTP_VERIFICATION.md](DEV_SMTP_VERIFICATION.md) | Dev SMTP and transactional email verification |
| [CONNECT_GMAIL_OUTLOOK.md](CONNECT_GMAIL_OUTLOOK.md) | Connecting Gmail and Outlook in the product |
| [GOOGLE_APIS_REQUIRED.md](GOOGLE_APIS_REQUIRED.md) | Google Cloud project and APIs required for Gmail |
| [PINECONE_SETUP.md](PINECONE_SETUP.md) | Pinecone vector index setup |

## Architecture & Planning

| Doc | Description |
|-----|-------------|
| [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | System architecture overview |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Database schema reference |
| [CAPACITY_AND_SCALING_SUMMARY.md](CAPACITY_AND_SCALING_SUMMARY.md) | Capacity and scaling summary |
| [SCHEMA_STRATEGY_LLM_DATA.md](SCHEMA_STRATEGY_LLM_DATA.md) | Schema strategy for LLM-related data |

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
| [E2E_TEST_PLAN.md](E2E_TEST_PLAN.md) | Playwright E2E test plan |
| [CURSOR_QUALITY_GATE.md](CURSOR_QUALITY_GATE.md) | Quality gate for automation, queues, and workflows |

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
| [CHATBOT_IMPLEMENTATION.md](CHATBOT_IMPLEMENTATION.md) | Chatbot implementation overview |
| [CHATBOT_FEEDBACK_API.md](CHATBOT_FEEDBACK_API.md) | Chatbot feedback API |
| [CHATBOT_KB_IMPORT.md](CHATBOT_KB_IMPORT.md) | Knowledge base import |
| [CHATBOT_KB_PIPELINE_MAP.md](CHATBOT_KB_PIPELINE_MAP.md) | Chatbot KB pipeline map |
| [CRM_LEAD_SCORING.md](CRM_LEAD_SCORING.md) | CRM lead scoring |
| [EXPERT_ESCALATION_IMPLEMENTATION.md](EXPERT_ESCALATION_IMPLEMENTATION.md) | Expert escalation implementation |
| [EXPERT_ESCALATION_SYSTEM.md](EXPERT_ESCALATION_SYSTEM.md) | Expert escalation system design |
| [EXPORT_IMPORT_DATA_FORMATS.md](EXPORT_IMPORT_DATA_FORMATS.md) | Export/import data formats |
| [IMPLEMENTATION_PROPOSAL_TEMPLATE.md](IMPLEMENTATION_PROPOSAL_TEMPLATE.md) | Template for implementation proposals |
| [KPI_TRACKING_SYSTEM.md](KPI_TRACKING_SYSTEM.md) | KPI tracking system |
| [TENANT_ISOLATION_IMPLEMENTATION.md](TENANT_ISOLATION_IMPLEMENTATION.md) | Tenant isolation implementation |

## Operations & Reliability

| Doc | Description |
|-----|-------------|
| [HEALTH_CHECK_GUIDE.md](HEALTH_CHECK_GUIDE.md) | Health check setup |
| [UPTIME_MONITORING_SETUP.md](UPTIME_MONITORING_SETUP.md) | Uptime monitoring |
| [monitoring-metrics.md](monitoring-metrics.md) | Prometheus metrics config |
| [DISASTER_RECOVERY_CHECKLIST.md](DISASTER_RECOVERY_CHECKLIST.md) | Disaster recovery procedures |
| [FINANCIAL_MODEL_AND_RATE_LIMITING.md](FINANCIAL_MODEL_AND_RATE_LIMITING.md) | Pricing, cost, rate limiting, capacity |
| [AUTOMATION_RELIABILITY.md](AUTOMATION_RELIABILITY.md) | Automation reliability |
| [BACKGROUND_JOBS_ARCHITECTURE.md](BACKGROUND_JOBS_ARCHITECTURE.md) | Background jobs architecture |
| [BACKUP_STRATEGY.md](BACKUP_STRATEGY.md) | Backup strategy |
| [CI_CD_STRATEGY.md](CI_CD_STRATEGY.md) | CI/CD strategy |
| [OPERATIONAL_SAFEGUARDS.md](OPERATIONAL_SAFEGUARDS.md) | Operational safeguards |
| [SLOs.md](SLOs.md) | Service level objectives |
| [STAGING_AND_PROVIDER_READINESS.md](STAGING_AND_PROVIDER_READINESS.md) | Staging and provider readiness |
| [WORKFLOW_DIAGNOSTIC_PLAYBOOK.md](WORKFLOW_DIAGNOSTIC_PLAYBOOK.md) | Workflow diagnostics playbook |

## Security & Debugging

| Doc | Description |
|-----|-------------|
| [SECURITY_ASSESSMENT.md](SECURITY_ASSESSMENT.md) | Security assessment report |
| [SECURITY_COST_CONTROL_PLAYBOOK.md](SECURITY_COST_CONTROL_PLAYBOOK.md) | Low-cost CASA pre-lab security workflow (OAuth scope) |
| [AUTHENTICATION_DEBUG_GUIDE.md](AUTHENTICATION_DEBUG_GUIDE.md) | Auth debugging guide |
| [TROUBLESHOOTING_GUIDE.md](TROUBLESHOOTING_GUIDE.md) | General troubleshooting |
| [WEBHOOK_SECURITY.md](WEBHOOK_SECURITY.md) | Webhook security |
| [STRUCTURED_LOGGING.md](STRUCTURED_LOGGING.md) | Structured logging |
| [TWILIO_WEBHOOKS.md](TWILIO_WEBHOOKS.md) | Twilio webhooks |

## Technical Deep Dives

| Doc | Description |
|-----|-------------|
| [CRUD_RAG_ARCHITECTURE.md](CRUD_RAG_ARCHITECTURE.md) | CRUD, RAG flow, identity/merge policy |
| [MUTEX_CONTENTION_MITIGATION.md](MUTEX_CONTENTION_MITIGATION.md) | Mutex contention fixes |
| [CORRELATION_AND_EVENTS.md](CORRELATION_AND_EVENTS.md) | Correlation IDs and events |
| [SQLITE_DATETIME_COMPARISONS.md](SQLITE_DATETIME_COMPARISONS.md) | SQLite datetime comparisons |
| [MIGRATIONS.md](MIGRATIONS.md) | Database migrations |

## Admin & developer tooling

| Doc | Description |
|-----|-------------|
| [ADMIN_ROUTES_STRATEGY.md](ADMIN_ROUTES_STRATEGY.md) | Admin routes and RBAC strategy |
| [AUTHORIZATION_MATRIX.md](AUTHORIZATION_MATRIX.md) | Authorization matrix |
| [CODEX_SETUP.md](CODEX_SETUP.md) | Codex setup for this repository |

## Reference

| Doc | Description |
|-----|-------------|
| [COMING_SOON.md](COMING_SOON.md) | Features not guaranteed / coming soon (UI and backend) |

## Migrations & dependency audits

| Doc | Description |
|-----|-------------|
| [POSTGRES_MIGRATION_AUDIT.md](POSTGRES_MIGRATION_AUDIT.md) | Postgres migration audit |
| [LEGACY_DEPENDENCY_AUDIT.md](LEGACY_DEPENDENCY_AUDIT.md) | Legacy dependency audit |
