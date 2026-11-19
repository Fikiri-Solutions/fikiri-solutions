# BNR Holdout — Case-Level Response Quality Review

**Date:** 2026-11-18  
**Set:** prior 30-case BNR holdout (`split=holdout`) — **previously observed during development; not a pristine release holdout**  
**Labels:** automated / provisional — **not independently dual-reviewed**  
**Generic consultation invitation ≠ full success** when the bot fails to acknowledge an identifiable customer problem.

## Summary

| Metric | Value |
|---|---|
| Cases | 30 |
| Auto-pass (draft grader) | **100%** |
| Need recognition (`need_hit`) | **93.3%** (28/30) |
| Fallback | **0%** |
| Unsupported claim hits | **0%** |
| `need_recognized_useful` | **28** |
| `useful_without_need_id` | **2** |
| `generic_consult` | **0** |
| `fallback` / `unsupported_claim` | **0** |

**Why 100% auto-pass can exceed 93.3% need_hit:** the draft grader accepts a useful answer mode even when the exact taxonomy `need_id` is missed. Quality review below separates those dimensions.

## Case table

| Case ID | Expected need | Quality | Need hit | Mode | Notes |
|---|---|---|---|---|---|
| bnr_scheduling_dispatch_08 | scheduling_dispatch | need_recognized_useful | Y | answer | Acknowledges scheduling/dispatch |
| bnr_scheduling_dispatch_09 | scheduling_dispatch | need_recognized_useful | Y | answer | Double-book / landscaping |
| bnr_customer_management_08 | customer_management | need_recognized_useful | Y | answer | Restaurant order history → CRM (was prior miss) |
| bnr_customer_management_09 | customer_management | need_recognized_useful | Y | answer | Client / customer view |
| bnr_followups_communication_08 | followups_communication | need_recognized_useful | Y | answer | Ownership of texts/emails |
| bnr_followups_communication_09 | followups_communication | need_recognized_useful | Y | answer | Cold leads / follow-up |
| bnr_document_automation_08 | document_automation | need_recognized_useful | Y | answer | Daily reports / paperwork |
| bnr_document_automation_09 | document_automation | need_recognized_useful | Y | answer | Rekeying forms |
| bnr_quotes_invoicing_08 | quotes_invoicing | need_recognized_useful | Y | answer | Proposals |
| bnr_quotes_invoicing_09 | quotes_invoicing | need_recognized_useful | Y | answer | Quotes stuck in drafts |
| bnr_lead_intake_08 | lead_intake | useful_without_need_id | N | answer | Useful intake/CRM bridge; taxonomy id miss |
| bnr_lead_intake_09 | lead_intake | need_recognized_useful | Y | answer | Interest forms / unanswered |
| bnr_customer_support_08 | customer_support | need_recognized_useful | Y | answer | Repeating enrollment Qs |
| bnr_customer_support_09 | customer_support | need_recognized_useful | Y | answer | Setup FAQs |
| bnr_reporting_analytics_08 | reporting_analytics | need_recognized_useful | Y | answer | Bakery who-pays → payment-status reporting (was prior miss) |
| bnr_reporting_analytics_09 | reporting_analytics | need_recognized_useful | Y | answer | Profitability / retainers |
| bnr_data_sync_08 | data_sync | useful_without_need_id | N | answer | Useful ops bridge; taxonomy id miss |
| bnr_data_sync_09 | data_sync | need_recognized_useful | Y | answer | Lists out of date |
| bnr_employee_coordination_08 | employee_coordination | need_recognized_useful | Y | answer | Field vs office status |
| bnr_employee_coordination_09 | employee_coordination | need_recognized_useful | Y | answer | Shift handoff |
| bnr_inventory_08 | inventory | need_recognized_useful | Y | answer | Parts duplication; limitation language |
| bnr_inventory_09 | inventory | need_recognized_useful | Y | answer | Color inventory |
| bnr_payments_billing_08 | payments_billing | need_recognized_useful | Y | answer | Dues collection |
| bnr_payments_billing_09 | payments_billing | need_recognized_useful | Y | answer | Ghosting after work |
| bnr_website_digital_ops_08 | website_digital_ops | need_recognized_useful | Y | answer | Forms → random inbox |
| bnr_website_digital_ops_09 | website_digital_ops | useful_without_need_id* | N* | answer | Useful; may map scheduling rather than website ops |
| bnr_integrations_08 | integrations | need_recognized_useful | Y | answer | QuickBooks + inbox |
| bnr_integrations_09 | integrations | need_recognized_useful | Y | answer | Shopify → ops |
| bnr_business_discovery_08 | business_discovery | need_recognized_useful | Y | answer | Duct-taped growth |
| bnr_business_discovery_09 | business_discovery | need_recognized_useful | Y | answer | Inherited mess / starting point |

\*Confirm on dual review; automated quality classifier marks useful when problem language appears even if expected `need_id` differs.

Machine-readable dump: `docs/FIKIRI_SITE_BOT_BNR_HOLDOUT_QUALITY_REVIEW.json`.

## Prior concept misses — root cause

| Case | Root cause | Fix (reusable, not industry-specific) |
|---|---|---|
| Restaurant order tracking | Empty need detection + weak CRM/order phrases; wrong bundle bleed (Lead Intake / Booking) | CRM concept phrases (`who ordered`, `order history`); suppress intake/booking bundles without phrase hits; taxonomy allowed claims in bridge |
| Bakery account payments | Empty need detection for payment-status reporting | Reporting phrases (`actually pay`, `outstanding balances`); Workflow Audit preferred; payment-status allowed claim |

## Still open for owner / release set

- 2 useful answers without exact expected `need_id` (lead intake / data sync style).
- Prior holdout is **contaminated** for final release scoring — use `tests/company_chatbot_bnr_release_candidate.yaml` after independent labeling.
