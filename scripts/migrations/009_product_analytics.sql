-- Additive: privacy-safe product analytics events (customer-success foundation).
-- Apply via psql / Supabase SQL editor against Postgres.
-- SQLite tests / local init also apply compatible DDL via db_optimizer.
--
-- tenant_id and actor_user_id are separate columns even when currently equal to the
-- account user id (future multi-member orgs).
-- Do not store secrets, email/CRM content, or raw session IDs (hash only).
--
-- Rollback: scripts/migrations/rollback/009_product_analytics.sql

CREATE TABLE IF NOT EXISTS product_events (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    actor_user_id INTEGER NOT NULL,
    event_name TEXT NOT NULL,
    event_source TEXT NOT NULL,
    feature_key TEXT,
    workflow_key TEXT,
    properties_json TEXT,
    occurred_at TIMESTAMP NOT NULL,
    received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    session_id_hash TEXT,
    correlation_id TEXT,
    schema_version INTEGER NOT NULL DEFAULT 1,
    outcome_dedupe_key TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_product_events_outcome_dedupe
    ON product_events (tenant_id, outcome_dedupe_key)
    WHERE outcome_dedupe_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_product_events_tenant_occurred
    ON product_events (tenant_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_product_events_tenant_name_occurred
    ON product_events (tenant_id, event_name, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_product_events_feature
    ON product_events (tenant_id, feature_key, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_product_events_workflow
    ON product_events (tenant_id, workflow_key, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_product_events_received
    ON product_events (received_at);

CREATE TABLE IF NOT EXISTS tenant_daily_metrics (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    metric_date TEXT NOT NULL,
    active_users INTEGER NOT NULL DEFAULT 0,
    sessions INTEGER NOT NULL DEFAULT 0,
    meaningful_actions INTEGER NOT NULL DEFAULT 0,
    workflow_started INTEGER NOT NULL DEFAULT 0,
    workflow_completed INTEGER NOT NULL DEFAULT 0,
    workflow_failed INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    feature_usage_json TEXT,
    accessibility_signal_counts_json TEXT,
    last_event_at TIMESTAMP,
    aggregated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, metric_date)
);

CREATE INDEX IF NOT EXISTS idx_tenant_daily_metrics_date
    ON tenant_daily_metrics (metric_date DESC);

CREATE INDEX IF NOT EXISTS idx_tenant_daily_metrics_updated
    ON tenant_daily_metrics (updated_at DESC);
