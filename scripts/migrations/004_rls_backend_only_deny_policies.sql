-- ============================================================================
-- Migration 004: Explicit deny-all RLS policies (backend-only tables)
-- ============================================================================
--
-- Source:  Supabase database linter (lint 0008_rls_enabled_no_policy)
-- Date:    2026-06-25
-- Status:  PENDING APPLICATION — apply via Supabase SQL editor or psql.
--
-- ----------------------------------------------------------------------------
-- Why this migration exists
-- ----------------------------------------------------------------------------
-- All public app tables have RLS enabled (lint 0013). The Flask backend
-- connects via DATABASE_URL / service role, which bypasses RLS. The frontend
-- does not query these tables via PostgREST (only Supabase Auth auto-refresh).
--
-- RLS with zero policies already denies anon/authenticated access. This
-- migration adds an explicit deny policy per table so the Supabase linter
-- stops reporting rls_enabled_no_policy INFO findings, and the intent is
-- documented in pg_policies.
--
-- Policy name: backend_only_no_api_access
-- Roles:       anon, authenticated (NOT service_role / postgres)
-- Effect:      USING (false) + WITH CHECK (false) — no API access
--
-- Idempotent: skips tables that already have any policy defined.

DO $$
DECLARE
  t text;
BEGIN
  FOR t IN
    SELECT c.relname
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relkind = 'r'
      AND c.relrowsecurity = true
      AND NOT EXISTS (
        SELECT 1
        FROM pg_policies p
        WHERE p.schemaname = 'public'
          AND p.tablename = c.relname
      )
  LOOP
    EXECUTE format(
      'CREATE POLICY backend_only_no_api_access ON public.%I '
      'FOR ALL TO anon, authenticated USING (false) WITH CHECK (false)',
      t
    );
  END LOOP;
END $$;
