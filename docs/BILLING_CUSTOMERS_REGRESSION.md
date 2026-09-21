# Billing customers — regression tests

Table: `public.billing_customers`  
Seeded: 2026-09-21 from `stripe_webhook_events` (4 Stripe clients, no app accounts)

## Why this table exists

Stripe invoice customers were arriving via webhooks but never becoming durable
customer records. Putting them in `users` / `contacts` / `leads` would break
auth uniqueness, invent passwords, or pollute tenant CRM.

## Bugs / gaps found during first seed (track these)

| ID | Severity | Finding | Expected regression check |
|----|----------|---------|---------------------------|
| BC-01 | High | New table was created **without RLS** while sibling billing tables (`stripe_webhook_events`, `subscriptions`) have RLS + deny-all. Fixed in same session. | After any new public table: `SELECT relrowsecurity FROM pg_class WHERE relname = '…'` must be `true`; anon/authenticated policy denies all. |
| BC-02 | Medium | `cus_Uz2AtBI11oCPz6` (info@aimhighhithigher.com) has **no name** in webhook history (`customer.created` missing / never logged). | Sync/upsert must allow NULL `name`/`business_name`; do not invent display names from domains. |
| BC-03 | Medium | CIRCA (`cus_V6rXe7SgFpSTSd`): invoice `amount_due` was **55000** but `payment_succeeded` recorded **27500**. | Prefer `invoice.payment_succeeded.amount_paid` for `total_paid_cents`; never assume amount_due == paid. |
| BC-04 | Medium | Financial Partner Group (`cus_VBJxCwXtAFmMGG`): **$625 invoice created**, no `payment_succeeded` in log. Status stored as `invoiced`, `total_paid_cents = 0`. | Status/paid totals must distinguish invoiced-unpaid vs paid; do not mark `active` paid without payment events. |
| BC-05 | Low | Stripe name **"Creating Good Prolems"** is misspelled at source. | Persist Stripe spelling as-is; corrections only via explicit admin edit, not auto “fix”. |
| BC-06 | High (process) | Test accidentally set `linked_user_id = 9` (admin). Cleared immediately. | `linked_user_id` must stay NULL until email matches a real `users` row for that customer; never link to operator/admin during tests. |

## Coexistence checks (must stay true)

Run against `fikiri-prod` (or staging mirror):

```sql
-- 1) No billing email is an app user yet (until they actually sign up)
SELECT COUNT(*) AS should_be_zero
FROM billing_customers bc
JOIN users u ON lower(u.email) = lower(bc.email);

-- 2) No accidental CRM pollution from this feature
-- (counts may grow from normal CRM use; assert no lead/contact with source='stripe_webhook'
--  unless a future feature intentionally adds that source)
SELECT COUNT(*) AS should_be_zero
FROM leads
WHERE source = 'stripe_webhook';

SELECT COUNT(*) AS should_be_zero
FROM contacts
WHERE source = 'stripe_webhook';

-- 3) Constraints
-- Duplicate stripe_customer_id → unique_violation
-- linked_user_id = 999999 → foreign_key_violation

-- 4) RLS on
SELECT c.relname, c.relrowsecurity
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname = 'billing_customers';
-- expect relrowsecurity = true
```

## Seeded baseline (do not delete without review)

| stripe_customer_id | email | status | total_paid_cents |
|--------------------|-------|--------|------------------|
| cus_V6rXe7SgFpSTSd | thompsonmaurice1@gmail.com | active | 27500 |
| cus_Uz2AtBI11oCPz6 | info@aimhighhithigher.com | active | 124970 |
| cus_V9l1iVkEFNhJOv | info@creatinggoodproblems.com | active | 60000 |
| cus_VBJxCwXtAFmMGG | financialpartnergroup@gmail.com | invoiced | 0 |

## Non-goals (until separately approved)

- Auto-creating `users` rows
- Wiring webhook handlers to upsert `billing_customers`
- Admin UI
- Linking on signup

## Pass criteria for this change

- [x] Table exists with unique `stripe_customer_id`
- [x] FK on `linked_user_id` enforced
- [x] Unique duplicate rejected
- [x] Four Stripe clients seeded; `linked_user_id` all NULL
- [x] Zero overlap with `users.email`
- [x] `users` / `contacts` / `leads` not used for storage
- [x] RLS enabled + deny-all for anon/authenticated
