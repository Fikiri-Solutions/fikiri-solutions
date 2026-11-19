# BNR Capability Claim Audit

**Status:** draft for owner approval — **do not treat as production clearance**  
**Sources checked:** `fikiri_business_need_taxonomy.json`, `fikiri_capability_map.json`, bridge composer (`compose_capability_bridge`), public-facing KB chunk IDs referenced by families/bundles.

## Classification legend

| Class | Meaning |
|---|---|
| Verified current service | Packaged / documented Fikiri product or standard engagement |
| Potential custom (discovery) | Reasonable consulting/custom scope; must not sound turnkey |
| Unsupported / unverified | Do not claim; clarify or hand off |

## Category audit

| Need | Code status | Audit class | Claim risk notes | Owner |
|---|---|---|---|---|
| scheduling_dispatch | custom_discovery | Potential custom | OK to discuss workflow/scheduling automation after discovery. **Forbidden:** logistics product, guaranteed on-time, driver app included. | |
| customer_management | verified | Verified current (+ custom for order history) | CRM contacts/activity/ownership verified. Order-history style = custom CRM workflow, not POS. | |
| followups_communication | verified | Verified current | Email follow-up / lead ownership OK. Do not promise SMS-to-every-driver OOTB. | |
| document_automation | custom_discovery | Potential custom | Process mapping first. No full DMS replacement claim. | |
| quotes_invoicing | custom_discovery | Potential custom | Scoped quote/invoice automation OK. No QuickBooks replacement / auto-pay without review. | |
| lead_intake | verified | Verified current | Form → CRM → follow-up path OK. No guaranteed conversion lift. | |
| customer_support | verified | Verified current | Knowledge answers + email triage OK. Not fully autonomous support always. | |
| reporting_analytics | verified_partial | Verified partial + custom | Plan analytics OK; payment-status / ops reporting = custom after discovery. No predictive profit AI on Starter. | |
| data_sync | custom_discovery | Potential custom | Integrate existing systems after discovery. No “sync every SaaS instantly.” | |
| employee_coordination | custom_discovery | Potential custom | Ownership/handoffs via workflow design. No full WFM suite OOTB. | |
| inventory | unsupported_or_discovery | Unsupported / discovery | Explicit non-packaged language required. No WMS / barcode inventory included. | |
| payments_billing | verified_partial | Verified partial + custom | Booking/payment workflows careful. No guaranteed collection. | |
| website_digital_ops | verified_boundary | Verified boundary | Connect intake to office workflows. Not a general WordPress agency. | |
| integrations | verified_partial | Verified partial | Gmail/Outlook + custom integrations after stack confirm. No every-ERP day one. | |
| business_discovery | verified | Verified current | Workflow discovery when solution unclear. | |

## Bridge / bundle claim checks

| Bundle | Audit | Notes |
|---|---|---|
| Lead Intake System | Verified current | Only when intake/website phrases hit (bleed suppressed for CRM/reporting-only queries). |
| Email Workflow Assistant | Verified current | Gmail/Outlook path; do not attach to pure order-tracking CRM asks. |
| Workflow Audit | Verified current | Preferred for reporting / mixed / discovery-heavy needs. |
| Booking and Payments Flow | Verified partial | Requires booking/payment phrases; suppressed on CRM/reporting-only. |
| Site Chat and Knowledge | Verified current | FAQ / routing; not CRM replacement. |

## Hard blocks (must never appear without evidence)

- Guaranteed integrations, delivery timelines, or payment collection
- Industry-specific turnkey systems (restaurant POS, courier logistics product, warehouse WMS)
- HIPAA certification claims
- “We wipe / delete customer data nightly” style destructive automation offers

## Uncertain claims needing owner approval

1. Payment-status / receivables reporting as custom CRM+reporting scope  
2. Scheduling/dispatch as custom workflow (vs generic “workflow automation” only)  
3. Whether Booking and Payments language is too strong for schedule-only asks  
4. Inventory always forces “not a packaged product” (recommended: yes)

See also: `docs/FIKIRI_SITE_BOT_BNR_OWNER_REVIEW.md`.
