-- Additive: anonymous public marketing-site funnel events (intake + chatbot).
-- No PII, no chat transcripts, no form free text.
-- Rollback: scripts/migrations/rollback/011_site_marketing_events.sql

CREATE TABLE IF NOT EXISTS site_marketing_events (
    id BIGSERIAL PRIMARY KEY,
    event_name TEXT NOT NULL,
    session_ref TEXT NOT NULL,
    dedupe_key TEXT NOT NULL DEFAULT '',
    properties_json TEXT,
    occurred_at TIMESTAMP NOT NULL,
    received_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    schema_version INTEGER NOT NULL DEFAULT 1
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_site_marketing_events_dedupe
    ON site_marketing_events (event_name, session_ref, dedupe_key);

CREATE INDEX IF NOT EXISTS idx_site_marketing_events_name_occurred
    ON site_marketing_events (event_name, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_site_marketing_events_occurred
    ON site_marketing_events (occurred_at DESC);
