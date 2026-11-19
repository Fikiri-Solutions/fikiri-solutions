# BNR Owner Review Sheet — Capability Claims & Labels

**Purpose:** Human approval of what the site bot may say. Automated labels are **not** independently verified.  
**Do not deploy** until critical rows are approved or rewritten.

## How to use

For each taxonomy category, mark:
- `APPROVE` — claim language OK as written  
- `EDIT` — rewrite allowed/forbidden claims  
- `BLOCK` — do not allow bridge answers for this need until clarified  

## Taxonomy claim matrix

| Need ID | Status in code | Allowed direction (summary) | Forbidden (summary) | Owner |
|---|---|---|---|---|
| scheduling_dispatch | custom_discovery | Custom workflow/scheduling after discovery; late notifications are potential use cases | Logistics product / guaranteed on-time / driver app included | |
| customer_management | verified | CRM contacts, conversations, activity, next steps; order-history style may be custom CRM workflow | POS replacement / turnkey order-management product | |
| followups_communication | verified | Email follow-up, lead ownership, structured replies | Out-of-box SMS-to-every-driver | |
| document_automation | custom_discovery | Document-heavy workflows after process mapping | Full DMS replacement today | |
| quotes_invoicing | custom_discovery | Quote/invoice automation as scoped custom work | QuickBooks replacement / auto-pay without review | |
| lead_intake | verified | Capture/route website inquiries | Guaranteed conversion lift | |
| customer_support | verified | Knowledge answers + email triage | Fully autonomous support always | |
| reporting_analytics | verified_partial | Plan analytics + custom operational/payment-status reporting | Predictive profit AI on Starter | |
| data_sync | custom_discovery | Reduce duplicate entry via integrations after discovery | Sync every SaaS instantly | |
| employee_coordination | custom_discovery | Ownership/handoffs via workflow design | Full WFM suite OOTB | |
| inventory | unsupported_or_discovery | Not a core packaged product; discuss custom integration | Warehouse WMS / barcode inventory included | |
| payments_billing | verified_partial | Booking/payment workflows; careful reminders | Guaranteed payment collection | |
| website_digital_ops | verified_boundary | Connect intake to office workflows; website design bounded | Full WordPress agency for any site | |
| integrations | verified_partial | Gmail/Outlook + custom integrations after stack confirmation | Every ERP day one | |
| business_discovery | verified | Start with workflow discovery when solution unclear | Fix everything without discovery | |

## Example target response (owner preferred)

> It sounds like you're trying to track which customers have outstanding balances and which accounts have paid. Fikiri builds custom CRM and business workflow solutions that may help with that. We'd need to understand your current payment and accounting systems before recommending an approach.

Mark whether bridge templates are close enough or need copy edits: ________

## Label review

- BNR 150 + FCRB 50 labels: `draft_unvalidated`
- Prior 30-case holdout was observed during development → **not** a pristine release holdout
- Fresh release set: `tests/company_chatbot_bnr_release_candidate.yaml` (requires independent human labeling before scoring claims)

## Questions needing owner verification

1. May the bot say Fikiri can help with **scheduling/dispatch** as custom work, or only “workflow automation” generically?  
2. Is **payment-status / receivables reporting** an allowed custom scope statement?  
3. Should inventory always force “not a packaged product” language (recommended: yes)?  
4. Is Booking and Payments bundle too strong when the user only mentioned crew schedules?
