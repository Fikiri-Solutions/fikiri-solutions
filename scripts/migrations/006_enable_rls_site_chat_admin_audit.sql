-- ============================================================================
-- Migration 006: Enable RLS on site_chat_* and admin_audit_log
-- ============================================================================
--
-- Source:  Supabase database linter
--          (lint 0013_rls_disabled_in_public, lint 0023_sensitive_columns_exposed)
-- Date:    2026-07-29
-- Status:  Apply via Supabase MCP / SQL editor / psql against Postgres.
--
-- ----------------------------------------------------------------------------
-- Why this migration exists
-- ----------------------------------------------------------------------------
-- Tables in the `public` schema exposed to PostgREST must have row-level
-- security enabled. These backend-only tables were created without RLS.
--
-- Access model: Flask connects via DATABASE_URL (postgres / service role),
-- which bypasses RLS. The frontend does not query these tables via PostgREST.
-- No permissive anon/authenticated policies — Data API clients cannot read
-- or write these rows. Explicit deny policies also clear lint 0008
-- (rls_enabled_no_policy).
--
-- Tables:
--   site_chat_sessions          — marketing-site chat session rollup
--   site_chat_messages          — chat transcript turns (PII risk)
--   site_chat_transcript_reads  — admin transcript read audit
--   admin_audit_log             — platform-admin privileged action log
--
-- Idempotent: safe to re-run.

ALTER TABLE public.site_chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.site_chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.site_chat_transcript_reads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_audit_log ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
  t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'site_chat_sessions',
    'site_chat_messages',
    'site_chat_transcript_reads',
    'admin_audit_log'
  ]
  LOOP
    IF NOT EXISTS (
      SELECT 1
      FROM pg_policies p
      WHERE p.schemaname = 'public'
        AND p.tablename = t
        AND p.policyname = 'backend_only_no_api_access'
    ) THEN
      EXECUTE format(
        'CREATE POLICY backend_only_no_api_access ON public.%I '
        'FOR ALL TO anon, authenticated USING (false) WITH CHECK (false)',
        t
      );
    END IF;
  END LOOP;
END $$;
