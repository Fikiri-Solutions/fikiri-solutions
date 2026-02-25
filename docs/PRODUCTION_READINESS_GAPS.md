# Production Readiness Gaps & Action Plan

**Status**: Identified gaps from architecture review (Feb 2026)  
**Priority**: Address before declaring production-grade

---

## 🔴 Critical Gaps (Must Fix)

### 1. Multi-Tenant Isolation

**Current State:**
- Vector search (`core/minimal_vector_search.py`) does NOT filter by `tenant_id`
- KB search (`core/knowledge_base_system.py`) has filters but no `tenant_id` filter
- Public chatbot gets `tenant_id` from API key but doesn't enforce it in retrieval
- **Risk**: Data leakage between customers

**Action Items:**

#### Vector Search Tenant Filtering
- [ ] Add `tenant_id` parameter to `search_similar()` in `MinimalVectorSearch`
- [ ] Store `tenant_id` in vector metadata when adding documents
- [ ] Filter by `tenant_id` in `_search_similar_local()` (in-memory)
- [ ] Filter by `tenant_id` in `_search_similar_pinecone()` (Pinecone metadata filter)
- [ ] Update `core/public_chatbot_api.py` to pass `tenant_id` to vector search
- [ ] Update `core/knowledge_base_system.py` to pass `tenant_id` when syncing to vector index

#### KB Search Tenant Filtering
- [ ] Add `tenant_id` filter support to `KnowledgeBaseSystem.search()`
- [ ] Ensure KB documents store `tenant_id` in metadata
- [ ] Update `core/public_chatbot_api.py` to pass `tenant_id` in KB search filters
- [ ] Update `core/chatbot_smart_faq_api.py` to enforce tenant isolation on CRUD

**Files to Modify:**
- `core/minimal_vector_search.py`
- `core/knowledge_base_system.py`
- `core/public_chatbot_api.py`
- `core/chatbot_smart_faq_api.py`

**Testing:**
- Unit tests: Verify tenant isolation in vector/KB search
- Integration test: Create two tenants, verify no cross-tenant data leakage

---

### 2. Flask + Sync I/O Blocking

**Current State:**
- Gmail/Outlook sync uses threading (not ideal for production)
- OpenAI/LLM calls can block request handlers
- Redis calls are sync (can block)
- **Risk**: Worker exhaustion, timeouts, poor scalability

**Action Items:**

#### Background Job Architecture
- [ ] Standardize on RQ (Redis Queue) for all long-running tasks
- [ ] Move Gmail sync from threading to RQ jobs (`email_automation/gmail_sync_jobs.py` already has RQ support, ensure it's used)
- [ ] Move email processing pipeline to RQ jobs
- [ ] Move AI/LLM heavy operations to RQ jobs (already partially in `core/redis_queues.py`)
- [ ] Add job status endpoints (`GET /api/jobs/<job_id>`)
- [ ] Add job retry logic with exponential backoff

#### Request Handler Timeouts
- [ ] Add Flask request timeout middleware (e.g., 30s max per request)
- [ ] Ensure all external API calls have timeouts (partially done, needs audit)
- [ ] Add circuit breakers for external APIs (OpenAI, Gmail, Stripe)

**Files to Modify:**
- `routes/business.py` (Gmail sync endpoint)
- `email_automation/gmail_sync_jobs.py` (ensure RQ usage)
- `core/redis_queues.py` (expand async processing)
- `app.py` (add request timeout middleware)

**Dependencies:**
- Ensure `rq` is in `requirements.txt`
- Ensure Redis is available in production

---

### 3. Operational Robustness

**Current State:**
- Backup system exists (`scripts/backup_system.py`) but not documented
- Migration examples exist (`scripts/migrations/`) but no Alembic setup
- Disaster recovery checklist exists but needs updates
- **Risk**: Data loss, migration failures, recovery delays

**Action Items:**

#### Database Migrations
- [ ] Set up Alembic for SQLite/PostgreSQL migrations
- [ ] Create initial Alembic migration from current schema
- [ ] Document migration workflow in `docs/MIGRATIONS.md`
- [ ] Add migration rollback procedures
- [ ] Add migration status endpoint (`GET /api/admin/migrations`)

#### Backup Strategy
- [ ] Document backup cadence (daily for prod, weekly for staging)
- [ ] Automate backups via cron/scheduler
- [ ] Test restore procedures quarterly
- [ ] Document backup retention policy (30 days? 90 days?)
- [ ] Add backup verification (checksums, test restores)

#### Disaster Recovery
- [ ] Update `docs/DISASTER_RECOVERY_CHECKLIST.md` with:
  - RTO (Recovery Time Objective): Target < 4 hours
  - RPO (Recovery Point Objective): Target < 24 hours
  - Step-by-step recovery procedures
  - Contact escalation list
- [ ] Document Redis recovery procedures
- [ ] Document environment variable backup/restore

**Files to Create/Modify:**
- `alembic.ini` (new)
- `alembic/env.py` (new)
- `alembic/versions/` (migration files)
- `docs/MIGRATIONS.md` (new)
- `docs/BACKUP_STRATEGY.md` (new)
- `docs/DISASTER_RECOVERY_CHECKLIST.md` (update)

---

## 🟡 High Priority Gaps

### 4. Authorization Model (RBAC)

**Current State:**
- JWT + sessions work for single-user accounts
- `require_role()` decorator exists but not widely used
- No org-level access control
- API keys have scopes but no user-level permissions
- **Risk**: Unauthorized access, no multi-user org support

**Action Items:**

#### Define Authorization Matrix
- [ ] Document required permissions for each endpoint:
  - CRM endpoints: `crm:read`, `crm:write`, `crm:delete`
  - KB endpoints: `kb:read`, `kb:write`, `kb:delete`
  - Automation endpoints: `automation:read`, `automation:write`, `automation:execute`
- [ ] Define roles: `owner`, `admin`, `member`, `viewer`
- [ ] Create authorization decorator: `require_permission(permission)`

#### Implement Org-Level Access Control
- [ ] Add `organization_id` to user model (if multi-org)
- [ ] Add `organization_id` to CRM leads/contacts
- [ ] Add `organization_id` to KB documents
- [ ] Filter queries by `organization_id` + user permissions
- [ ] Add org membership checks in all CRUD operations

**Files to Create/Modify:**
- `docs/AUTHORIZATION_MATRIX.md` (new)
- `core/authorization.py` (new or enhance `core/security.py`)
- `routes/business.py` (add permission checks)
- `core/chatbot_smart_faq_api.py` (add permission checks)

---

### 5. Data Lifecycle & Retention

**Current State:**
- User-level deletion exists (`core/privacy_manager.py`)
- No per-contact delete (documented in `CRUD_RAG_ARCHITECTURE.md`)
- No retention policies
- **Risk**: GDPR/compliance issues, storage bloat

**Action Items:**

#### Per-Contact Delete
- [ ] Add `delete_contact(contact_id, user_id)` to `crm/service.py`
- [ ] Soft-delete option (mark as deleted, anonymize after retention period)
- [ ] Add endpoint: `DELETE /api/crm/contacts/<id>`
- [ ] Update `CRUD_RAG_ARCHITECTURE.md` when implemented

#### Retention Policies
- [ ] Define retention periods:
  - Inactive leads: 2 years
  - Deleted contacts: 90 days (soft-delete) → then anonymize
  - Email threads: 1 year (or configurable)
  - KB documents: No expiration (or configurable)
- [ ] Implement retention job (`core/retention_jobs.py`)
- [ ] Schedule retention cleanup (weekly)

**Files to Create/Modify:**
- `crm/service.py` (add `delete_contact`)
- `routes/business.py` (add delete endpoint)
- `core/retention_jobs.py` (new)
- `docs/DATA_RETENTION_POLICY.md` (new)

---

### 6. Observability & SLOs

**Current State:**
- Trace IDs exist in LLM pipeline (`core/ai/llm_client.py`, `core/ai/llm_router.py`)
- Request IDs exist in monitoring (`core/monitoring.py`)
- Sentry for error tracking
- **Gap**: Not consistent across all flows, no SLOs defined

**Action Items:**

#### Structured Logging
- [ ] Ensure all log entries include:
  - `trace_id` (request-scoped)
  - `user_id` (when available)
  - `service` (email|crm|ai|integration)
  - `latency_ms` (for API calls)
  - `cost_usd` (for LLM calls)
- [ ] Use single logging utility (`core/structured_logging.py` exists, ensure it's used everywhere)
- [ ] Add trace ID propagation to:
  - Webhook processing (`core/webhook_api.py`)
  - Email pipeline (`email_automation/pipeline.py`)
  - Background jobs (RQ jobs)

#### Define SLOs
- [ ] Document target SLOs:
  - API latency: p95 < 500ms, p99 < 2s
  - LLM latency: p95 < 5s, p99 < 15s
  - Error rate: < 0.1% (excluding user errors)
  - Uptime: 99.9% (monthly)
- [ ] Add SLO monitoring dashboard
- [ ] Add alerting when SLOs are breached

**Files to Create/Modify:**
- `docs/SLOs.md` (new)
- `core/structured_logging.py` (ensure consistent usage)
- `analytics/monitoring_api.py` (add SLO metrics)
- All service files (add trace ID propagation)

---

## 🟢 Pragmatic Improvements

### 7. Timeouts & Circuit Breakers

**Current State:**
- Some timeouts exist (OAuth: 30s, webhooks: 10s, health: 3s)
- No circuit breakers
- **Gap**: Inconsistent, no protection against cascading failures

**Action Items:**

#### Add Timeouts Everywhere
- [ ] Audit all external API calls:
  - OpenAI API: 30s timeout
  - Gmail API: 30s timeout
  - Stripe API: 10s timeout
  - Redis: 5s timeout (already in `redis_connection_helper.py`)
- [ ] Add request-level timeout middleware (30s max)

#### Circuit Breakers
- [ ] Implement circuit breaker pattern for:
  - OpenAI API (fail open after 5 failures in 60s)
  - Gmail API (fail open after 3 failures in 60s)
  - Stripe API (fail closed, alert immediately)
- [ ] Add circuit breaker status endpoint (`GET /api/admin/circuit-breakers`)

**Files to Create/Modify:**
- `core/circuit_breaker.py` (new)
- `core/ai/llm_client.py` (add circuit breaker)
- `integrations/gmail/gmail_client.py` (add circuit breaker)
- `core/billing_api.py` (add circuit breaker for Stripe)

---

## Implementation Priority

1. **Week 1**: Multi-tenant isolation (critical security fix)
2. **Week 2**: Background jobs + timeouts (scalability)
3. **Week 3**: Migrations + backups (operational robustness)
4. **Week 4**: Authorization matrix + per-contact delete (compliance)
5. **Ongoing**: Observability improvements (SLOs, structured logging)

---

## Testing Requirements

For each gap fix:
- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual testing in staging
- [ ] Performance testing (for scalability changes)

---

## Documentation Updates

- [ ] Update `docs/SYSTEM_ARCHITECTURE.md` with new patterns
- [ ] Update `docs/CRUD_RAG_ARCHITECTURE.md` with tenant filtering
- [ ] Create `docs/PRODUCTION_CHECKLIST.md` (pre-deployment checklist)
- [ ] Update `README.md` with production deployment notes

---

*Last updated: Feb 2026*
