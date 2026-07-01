-- ============================================================================
-- Migration 003: Enable RLS on synced_emails and stripe_webhook_events
-- ============================================================================
--
-- Source:  Supabase database linter (lint 0013_rls_disabled_in_public)
-- Date:    2026-06-25
-- Status:  PENDING APPLICATION — apply via Supabase SQL editor or psql.
--
-- ----------------------------------------------------------------------------
-- Why this migration exists
-- ----------------------------------------------------------------------------
-- Tables in the `public` schema exposed to PostgREST must have row-level
-- security enabled. These two backend-only tables were created after the
-- bulk RLS rollout documented in docs/POSTGRES_MIGRATION_AUDIT.md.
--
-- Both tables are accessed exclusively by the Flask backend via DATABASE_URL
-- (service role / postgres), which bypasses RLS. No anon/authenticated
-- policies are defined — PostgREST clients cannot read or write these rows.
--
-- ----------------------------------------------------------------------------
-- Tables
-- ----------------------------------------------------------------------------
-- synced_emails          — Gmail/Outlook sync cache (user_id scoped in app)
-- stripe_webhook_events  — Stripe webhook idempotency ledger (no user_id)
--
-- Idempotent: safe to re-run (ALTER TABLE ... ENABLE ROW LEVEL SECURITY is
-- a no-op when RLS is already enabled).

ALTER TABLE public.synced_emails ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stripe_webhook_events ENABLE ROW LEVEL SECURITY;
