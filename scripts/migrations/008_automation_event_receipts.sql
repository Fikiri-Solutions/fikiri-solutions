-- Additive: durable automation ingress receipts (Windmill CE pilot).
-- Apply via psql / Supabase SQL editor against Postgres.
-- SQLite tests apply the same DDL through db_optimizer (BIGSERIAL → AUTOINCREMENT).
--
-- Idempotency identity: UNIQUE(source, event_id)
-- Ownership: INSERT status='processing' first; conflict never re-processes.
-- Do not store full response bodies — result_code only.
--
-- Rollback (manual): scripts/migrations/rollback/008_automation_event_receipts.sql
-- Kept outside naive *.sql forward globs under scripts/migrations/.

CREATE TABLE IF NOT EXISTS automation_event_receipts (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_version INTEGER NOT NULL,
    tenant_id TEXT,
    correlation_id TEXT NOT NULL,
    api_key_id INTEGER,
    actor_user_id INTEGER,
    request_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    result_code TEXT,
    error_code TEXT,
    received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE (source, event_id)
);

CREATE INDEX IF NOT EXISTS idx_automation_event_receipts_status_received
    ON automation_event_receipts (status, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_automation_event_receipts_correlation
    ON automation_event_receipts (correlation_id);
