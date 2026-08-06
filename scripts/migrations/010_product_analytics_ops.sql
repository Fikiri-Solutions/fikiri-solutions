-- Additive: product analytics ops daily counters (rollout observability).
-- Read/write by analytics emit+ingest only; admin APIs are read-only consumers.
-- Rollback: scripts/migrations/rollback/010_product_analytics_ops.sql

CREATE TABLE IF NOT EXISTS product_analytics_ops_daily (
    id BIGSERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL,
    metric_date TEXT NOT NULL,
    storage_failures INTEGER NOT NULL DEFAULT 0,
    rejected_events INTEGER NOT NULL DEFAULT 0,
    unexpected_errors INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, metric_date)
);

CREATE INDEX IF NOT EXISTS idx_product_analytics_ops_daily_date
    ON product_analytics_ops_daily (metric_date DESC);
