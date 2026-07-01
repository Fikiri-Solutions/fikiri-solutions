-- Phase 5b: Fikiri marketing site bot transcript tables (additive).
-- Applied automatically at runtime via company_chatbot/transcript_store.py
-- ensure_site_chat_transcript_tables(); this file is reference for Postgres ops.

CREATE TABLE IF NOT EXISTS site_chat_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    source_page TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    turn_count INTEGER NOT NULL DEFAULT 0,
    last_mode TEXT,
    latest_lead_tier TEXT,
    latest_lead_score INTEGER,
    latest_lead_synopsis TEXT,
    latest_handoff_path TEXT,
    hashed_ip TEXT,
    hashed_user_agent TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS site_chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    mode TEXT,
    grounded INTEGER,
    confidence REAL,
    sources_json TEXT,
    intake_json TEXT,
    handoff_json TEXT,
    lead_assessment_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS site_chat_transcript_reads (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    reader_user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_site_chat_sessions_last_seen
    ON site_chat_sessions (last_seen_at DESC);

CREATE INDEX IF NOT EXISTS idx_site_chat_messages_session_time
    ON site_chat_messages (session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_site_chat_transcript_reads_session
    ON site_chat_transcript_reads (session_id, created_at DESC);
