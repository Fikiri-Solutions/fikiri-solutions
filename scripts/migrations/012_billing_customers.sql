-- ============================================================================
-- Migration 012: billing_customers (Stripe-paid clients without app accounts)
-- ============================================================================
--
-- Date:    2026-09-21
-- Status:  Applied to fikiri-prod via Supabase MCP (create_billing_customers +
--          enable_rls_billing_customers). This file is the repo mirror.
--
-- Purpose:
--   Document paying Stripe customers who have not signed up for Fikiri yet.
--   Isolated from auth (users) and tenant CRM (contacts/leads).
--
-- Coexistence rules:
--   - Do NOT insert these emails into users (blocks signup; requires password_hash).
--   - Do NOT put them in contacts/leads (tenant-scoped CRM, wrong ownership model).
--   - linked_user_id stays NULL until a real users row exists for that customer.
--   - Flask/service-role DB access bypasses RLS; PostgREST anon/auth is denied.

CREATE TABLE IF NOT EXISTS public.billing_customers (
  id BIGSERIAL PRIMARY KEY,
  stripe_customer_id TEXT NOT NULL,
  email TEXT,
  name TEXT,
  business_name TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  first_seen_at TIMESTAMPTZ,
  last_payment_at TIMESTAMPTZ,
  total_paid_cents BIGINT NOT NULL DEFAULT 0,
  source TEXT NOT NULL DEFAULT 'stripe_webhook',
  linked_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
  metadata TEXT NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT billing_customers_stripe_customer_id_key UNIQUE (stripe_customer_id)
);

CREATE INDEX IF NOT EXISTS idx_billing_customers_email
  ON public.billing_customers (lower(email));
CREATE INDEX IF NOT EXISTS idx_billing_customers_linked_user_id
  ON public.billing_customers (linked_user_id);
CREATE INDEX IF NOT EXISTS idx_billing_customers_status
  ON public.billing_customers (status);

COMMENT ON TABLE public.billing_customers IS
  'Stripe-sourced paying clients who may not have Fikiri app accounts yet. Isolated from auth/CRM.';
COMMENT ON COLUMN public.billing_customers.linked_user_id IS
  'Set only after a real users row is created for this email/customer.';

ALTER TABLE public.billing_customers ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'billing_customers'
      AND policyname = 'billing_customers_deny_all'
  ) THEN
    CREATE POLICY billing_customers_deny_all
      ON public.billing_customers
      FOR ALL
      TO anon, authenticated
      USING (false)
      WITH CHECK (false);
  END IF;
END $$;
