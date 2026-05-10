-- ============================================================================
-- Migration 002: Promote TEXT-typed temporal columns to native PG types
-- ============================================================================
--
-- Source:  docs/POSTGRES_MIGRATION_AUDIT.md (Q3 schema-drift section).
-- Date:    2026-05-10
-- Status:  PENDING APPLICATION — apply via Supabase SQL editor, the
--          `apply_migration` MCP (when write mode is enabled), or psql.
--
-- ----------------------------------------------------------------------------
-- Why this migration exists
-- ----------------------------------------------------------------------------
-- Six columns were declared as TEXT in the bootstrap DDL even though their
-- names ("created_at", "started_at", "completed_at", "requested_date",
-- "requested_time") clearly represent dates / times. On Postgres, comparing
-- TEXT to TIMESTAMPTZ fails with
--   `operator does not exist: text > timestamp with time zone`.
--
-- Until now we worked around this by wrapping comparison sites with
-- `db_optimizer._pg_ts(col)` (cast to timestamptz on read). That cast stays
-- in the helpers as a defensive shim, but after this migration it becomes a
-- no-op against these columns — exactly what we want. The "no workarounds"
-- rule from .cursorrules is honored: fix the schema, don't decorate every
-- WHERE clause with a cast.
--
-- ----------------------------------------------------------------------------
-- Pre-migration verification (2026-05-10 via Supabase MCP)
-- ----------------------------------------------------------------------------
-- All four affected tables held ZERO rows at audit time:
--   - automation_jobs                                  rows: 0
--   - automation_run_events                            rows: 0
--   - customer_appointment_intake_submissions          rows: 0
--
-- This makes ALTER COLUMN TYPE a no-cost operation (no data rewrite).
--
-- ----------------------------------------------------------------------------
-- What this migration changes
-- ----------------------------------------------------------------------------
-- automation_jobs
--   created_at      text -> timestamptz NOT NULL DEFAULT now()
--   started_at      text -> timestamptz
--   completed_at    text -> timestamptz
--
-- automation_run_events
--   created_at      text -> timestamptz NOT NULL DEFAULT now()
--
-- customer_appointment_intake_submissions
--   requested_date  text -> date
--   requested_time  text -> time
--
-- ----------------------------------------------------------------------------
-- What this migration does NOT change
-- ----------------------------------------------------------------------------
-- - Application code: the read paths in services/automation_queue.py were
--   made shape-tolerant in the same PR (`_row_value_as_iso` /
--   `_row_value_as_datetime` helpers), so they work pre- and post-migration.
-- - The `db_optimizer._pg_ts()` cast helper and the `sql_column_newer_than_*`
--   /  `sql_timestamp_*` helpers stay in place. They become a free no-op
--   against TIMESTAMPTZ columns (timestamptz::timestamptz) and continue to
--   protect any future TEXT-typed `_at` column from breaking on Postgres.
-- - Indexes: only one index touches a column being altered
--   (idx_automation_run_events_user_created on (user_id, created_at DESC)),
--   and Postgres rebuilds it automatically. Empty table -> instant.
--
-- ----------------------------------------------------------------------------
-- How to apply
-- ----------------------------------------------------------------------------
-- Option A (Supabase dashboard):
--   1. Open the Supabase project SQL editor.
--   2. Paste the BODY below (everything from `BEGIN;` through `COMMIT;`).
--   3. Run as a single transaction.
--
-- Option B (Supabase MCP `apply_migration` with write mode enabled):
--   Name:   pg_audit_promote_text_timestamps_to_native_types
--   Query:  the BODY below (without the BEGIN/COMMIT wrapper — `apply_migration`
--           handles the transaction).
--
-- Option C (psql against DATABASE_URL):
--   psql "$DATABASE_URL" -f scripts/migrations/002_pg_audit_promote_text_timestamps.sql
--
-- ============================================================================

BEGIN;

ALTER TABLE public.automation_jobs
    ALTER COLUMN created_at TYPE timestamptz USING created_at::timestamptz,
    ALTER COLUMN created_at SET DEFAULT now(),
    ALTER COLUMN started_at TYPE timestamptz USING started_at::timestamptz,
    ALTER COLUMN completed_at TYPE timestamptz USING completed_at::timestamptz;

ALTER TABLE public.automation_run_events
    ALTER COLUMN created_at TYPE timestamptz USING created_at::timestamptz,
    ALTER COLUMN created_at SET DEFAULT now();

ALTER TABLE public.customer_appointment_intake_submissions
    ALTER COLUMN requested_date TYPE date USING NULLIF(requested_date, '')::date,
    ALTER COLUMN requested_time TYPE time USING NULLIF(requested_time, '')::time;

COMMIT;

-- Post-migration verification query (run after applying):
--
-- SELECT table_name, column_name, data_type
-- FROM information_schema.columns
-- WHERE table_schema = 'public'
--   AND (
--     (table_name = 'automation_jobs'
--        AND column_name IN ('created_at','started_at','completed_at'))
--     OR (table_name = 'automation_run_events'
--        AND column_name = 'created_at')
--     OR (table_name = 'customer_appointment_intake_submissions'
--        AND column_name IN ('requested_date','requested_time'))
--   )
-- ORDER BY table_name, column_name;
--
-- Expected output:
--   automation_jobs                          | completed_at   | timestamp with time zone
--   automation_jobs                          | created_at     | timestamp with time zone
--   automation_jobs                          | started_at     | timestamp with time zone
--   automation_run_events                    | created_at     | timestamp with time zone
--   customer_appointment_intake_submissions  | requested_date | date
--   customer_appointment_intake_submissions  | requested_time | time without time zone
