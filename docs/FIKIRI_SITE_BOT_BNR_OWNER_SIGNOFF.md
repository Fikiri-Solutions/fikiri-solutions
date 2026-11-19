# Fikiri Site Bot — Owner Sign-Off Report (BNR)

**Status:** Owner approved 2026-11-18 — shipping BNR + transcript study logging  
**Prepared:** 2026-11-18  
**Scope:** Deterministic business-need recognition + capability bridge  
**Owner decision:** APPROVE (deploy/update chatbot; keep collecting chat history for study/training)

---

## Executive verdict

| Question | Answer |
|---|---|
| Architecture direction | **Owner approved** |
| Production deploy | **Authorized** by owner — ship BNR update; keep `FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS=1` |
| Chat history / study logs | Persist stays on; turns store `meta_json` study labels (need ids + routing) for review/training |
| Labels | Draft / provisional — **not** independently reviewed |
| Prior 30 holdout | Previously observed during development — **not** a pristine release holdout |
| Fresh release set | 24 scenarios — awaiting independent labels; **do not tune against it** |

---

## 1. Capability approval matrix

Mark each row: **APPROVE** / **EDIT** / **BLOCK**.  
Claims are proposed only — **none are preapproved**.

Supporting sources are KB chunk IDs in `data/company_chatbot/fikiri_kb_chunks.jsonl` (via capability family mappings).

| # | Category | Proposed customer-facing claim | Supporting sources | Class | Example chatbot response (live) | Overpromise / unsupported risk | Owner |
|---|---|---|---|---|---|---|---|
| 1 | Scheduling and dispatch | “Fikiri builds custom workflow and scheduling-related automation after discovering your current tools.” (+ optional: late notifications are potential custom use cases, not turnkey guarantees) | `service_workflow_audit`, `service_workflow_audit_focus`, `faq_automation_partial`, `workflow_five_beats` | Custom discovery | See §2 logistics (holdout-style scheduling) | Logistics product; guaranteed on-time; driver app included | ☐ APPROVE ☐ EDIT ☐ BLOCK |
| 2 | Customer management | “Fikiri CRM helps small teams track contacts, conversations, activity, and next steps.” / order-history: “Order-history style tracking may be a CRM/custom workflow fit after discovery — not a turnkey POS.” | `product_crm_overview`, `product_crm_activity`, `product_crm_practical` | Verified current (+ custom for order history) | See §2 restaurant | POS / turnkey order-management; Salesforce-scale replacement | ☐ APPROVE ☐ EDIT ☐ BLOCK |
| 3 | Follow-ups and communication | “Fikiri helps with email follow-up, lead ownership, and structured replies.” | `product_ai_email_assistant`, `product_email_overview`, `integration_gmail`, `integration_outlook`, `product_crm_overview` | Verified current | See §2 informal email | SMS-to-every-driver OOTB | ☐ APPROVE ☐ EDIT ☐ BLOCK |
| 4 | Document automation | “Document-heavy workflows can often be automated after mapping your process.” | `service_workflow_audit`, `service_consulting`, `faq_automation_partial` | Custom discovery | *(pattern same as workflow-audit bridge; no dedicated §2 sample)* | Full DMS replacement today | ☐ APPROVE ☐ EDIT ☐ BLOCK |
| 5 | Estimates and invoicing | “Quote and invoice automation is a common custom workflow Fikiri scopes after discovery.” | `contact_intake_path`, `service_workflow_audit`, `workflow_inquiry_leak` | Custom discovery | *(no dedicated §2 sample)* | QuickBooks replacement; auto-pay without review | ☐ APPROVE ☐ EDIT ☐ BLOCK |
| 6 | Lead intake | “Fikiri helps capture and route website inquiries so leads do not sit unowned.” | `contact_intake_path`, `workflow_inquiry_leak`, `product_crm_overview` | Verified current | *(covered by Lead Intake System path in informal/intake bridges)* | Guaranteed conversion lift | ☐ APPROVE ☐ EDIT ☐ BLOCK |
| 7 | Customer support | “Fikiri can support knowledge-based answers and email triage for repeating customer questions.” | `site_chat_widget`, `product_ai_email_assistant`, `product_email_overview` | Verified current | *(FAQ/support path; HIPAA contrast in RC sheet)* | Fully autonomous support always; HIPAA certification | ☐ APPROVE ☐ EDIT ☐ BLOCK |
| 8 | Reporting and analytics | “Fikiri includes basic analytics on plans and can help design operational or payment-status reporting in custom work.” / “Seeing which accounts have paid vs outstanding is often a CRM + reporting workflow scoped after discovery.” | `pricing_starter`, `company_outcomes`, `service_workflow_audit`, `engagement_how_we_work` | Verified partial + custom | See §2 bakery | Predictive profit AI on Starter; guaranteed receivables collection | ☐ APPROVE ☐ EDIT ☐ BLOCK |
| 9 | Data entry / sync | “Reducing duplicate data entry usually means integrating the systems you already use — Fikiri scopes that after discovery.” | `service_workflow_audit`, `faq_automation_partial`, `workflow_five_beats` | Custom discovery | *(no dedicated §2 sample)* | Sync every SaaS instantly | ☐ APPROVE ☐ EDIT ☐ BLOCK |
| 10 | Employee coordination | “Clear ownership and handoffs are a common workflow-design outcome in Fikiri engagements.” | `product_crm_*`, `service_workflow_audit`, `workflow_five_beats` | Custom discovery | *(no dedicated §2 sample)* | Full WFM suite OOTB | ☐ APPROVE ☐ EDIT ☐ BLOCK |
| 11 | Inventory tracking | “Inventory systems are not a core packaged Fikiri product; we can discuss whether a custom integration fits.” | `service_workflow_audit`, `engagement_scoped_buildouts` | Unsupported / discovery only | *(limitation language required)* | Warehouse WMS; barcode inventory included | ☐ APPROVE ☐ EDIT ☐ BLOCK |
| 12 | Payments and billing | “Booking and payment-related workflows are in Fikiri's scope for appropriate builds; reminders can be designed carefully.” | `workflow_inquiry_leak`, `industry_dental_medical`, `service_workflow_audit` | Verified partial + custom | Related: bakery payment-status (reporting) | Guaranteed payment collection; Booking bundle on schedule-only asks | ☐ APPROVE ☐ EDIT ☐ BLOCK |
| 13 | Website / digital ops | “Fikiri focuses on connecting digital intake to office workflows; full WordPress design is bounded.” | `boundary_websites`, `contact_intake_path`, `product_crm_overview` | Verified boundary | *(no dedicated §2 sample)* | Full WordPress agency for any site | ☐ APPROVE ☐ EDIT ☐ BLOCK |
| 14 | Integrations | “Fikiri supports Gmail/Outlook email workflows and custom integrations after confirming your stack.” | `integration_gmail`, `integration_outlook`, `product_email_*`, `faq_automation_partial` | Verified partial | See §2 informal email (Gmail/Outlook) | Every ERP day one | ☐ APPROVE ☐ EDIT ☐ BLOCK |
| 15 | Business discovery | “Fikiri often starts with workflow discovery when the problem is clear but the solution is not.” | `service_workflow_audit`, `service_consulting`, `engagement_how_we_work` | Verified current | See §2 Jamaican (BNR-style) + ambiguous (BNR-style) | Fix everything without discovery | ☐ APPROVE ☐ EDIT ☐ BLOCK |

### Owner questions (must answer before deploy)

1. Scheduling/dispatch: allow “custom scheduling” language, or only generic “workflow automation”?  
2. Payment-status / receivables reporting: allowed as custom CRM+reporting scope?  
3. Inventory: always force “not a packaged product” (recommended: yes)?  
4. Is Booking and Payments wording too strong when the user only mentioned schedules?

### Preferred customer-style target (owner reference)

> It sounds like you're trying to track which customers have outstanding balances and which accounts have paid. Fikiri builds custom CRM and business workflow solutions that may help with that. We'd need to understand your current payment and accounting systems before recommending an approach.

Bridge templates are close on bakery; mark if copy edits are required: ________

---

## 2. Response quality evidence

Live responses captured from the current working tree (2026-11-18).  
**TESTED** = exact / near-exact BNR or holdout wording. **UNTESTED** = release-candidate wording not previously used to tune, or fresh paraphrase.

### A. Logistics scheduling and notifications

**TESTED (holdout-adjacent)** — user:  
`cleaning company staff schedules all over the place, who is on which job`  
Mode: `answer`

> That sounds like a scheduling and dispatch problem, which often connects to workflow automation and consulting and workflow audit. Delivery schedules and late notifications are potential custom use cases, not turnkey guarantees. It is closest to our Workflow Audit path: Map the current process, find manual handoffs, and recommend the first automation instead of guessing which product to buy. A workflow audit at fikirisolutions.com/intake is the safest first step when the scope is still mixed.

**UNTESTED / unresolved failure** — release-candidate courier wording:  
`I run a small courier service. Drivers clash on routes and customers call when we're late.`  
Mode: `fallback` — need detection empty; generic menu reply.  
**Do not tune against this RC case.** Record as open release-set risk.

### B. Restaurant order tracking — **TESTED holdout**

User: `restaurant regulars — how do I track who ordered what last time`  
Mode: `answer`

> That sounds like a customer management problem, which often connects to CRM and lead tracking and email and inbox automation. Order-history style tracking may be a CRM/custom workflow fit after discovery — not a turnkey POS. Fikiri can help with the related capabilities above; tell me which part matters most or ask to talk with the team.

### C. Bakery customer payment tracking — **TESTED holdout**

User: `bakery wholesale accounts — which ones actually pay`  
Mode: `answer`

> That sounds like a reporting and analytics problem, which often connects to reporting and dashboards and consulting and workflow audit. Seeing which accounts have paid vs outstanding is often a CRM + reporting workflow scoped after discovery. It is closest to our Workflow Audit path: Map the current process, find manual handoffs, and recommend the first automation instead of guessing which product to buy. A workflow audit at fikirisolutions.com/intake is the safest first step when the scope is still mixed.

### D. Informal email automation — **TESTED-style**

User: `honestly im drowning in emails and nobody follows up`  
Mode: `answer`

> That sounds like a mix of email and inbox automation, CRM and lead tracking, and workflow automation. It is closest to our Email Workflow Assistant path: Inbox triage, draft replies, lead detection, and follow-up reminders work together so email stops being the bottleneck. The likely capabilities are send follow-up. Fikiri's AI email assistant classifies and routes inbound mail, helps draft and structure replies, and works with Gmail and Outlook for small-team email workflows. If Gmail or Outlook is where work piles up, email automation is usually the first scoped build.

### E. Jamaican-influenced English

**TESTED BNR-style** — user: `mi office chaotic, whey fi fix first`  
Mode: `answer`

> That sounds like a business discovery / unclear needs problem, which often connects to consulting and workflow audit. Fikiri often starts with workflow discovery when the problem is clear but the solution is not. It is closest to our Workflow Audit path…

**UNTESTED / unresolved failure** — RC wording: `Tings inefficient but mi nuh know whey fi start.` → `fallback`. Open release-set risk; **do not tune**.

### F. Explicit human help — **TESTED**

User: `This is getting specific — can I talk to someone on your team?`  
Mode: `contact`

> You can reach us at info@fikirisolutions.com or use our contact page. An in-widget form will be available in a later release.

### G. Ambiguous business request

**TESTED BNR-style** — user: `process feels stuck and i dont know what i need`  
Mode: `answer` → business discovery / Workflow Audit path (same pattern as E).

**UNTESTED / unresolved failure** — RC wording: `idk things feel stuck` → `fallback`. Open release-set risk; **do not tune**.

### Prior holdout quality snapshot (historical / observed)

| Quality class | Count / 30 |
|---|---|
| need_recognized_useful | 28 |
| useful_without_need_id | 2 |
| generic_consult | 0 |
| Need recognition | 93.3% |
| Draft auto-pass | 100% |

Automated labels remain **draft_unvalidated**.

---

## 3. Independent release candidate

| Item | Value |
|---|---|
| File | `tests/company_chatbot_bnr_release_candidate.yaml` |
| Scenario count | **24** |
| Review status | `awaiting_independent_labels` |
| Used for tuning | **false** (all cases) |
| Do not | Score as final release until independently labeled; do not quietly rewrite expectations |

### Label sheet (owner / reviewer)

For each case: set `label_ok` = Y/N, optional `need_id_override`, notes.  
Provisional `need_id` in file is **author draft only** — not independent review.

| ID | Draft need (unvalidated) | Language | User utterance | Label OK? | Need override | Notes |
|---|---|---|---|---|---|---|
| rc_sched_01 | scheduling_dispatch | standard_en | Our service vans keep overlapping appointments on the same afternoon. | | | |
| rc_crm_orders_01 | customer_management | standard_en | I need to see which customers ordered from us last month and what they bought. | | | |
| rc_pay_status_01 | reporting_analytics | informal_us | honestly i cant tell which accounts paid and which still owe us | | | |
| rc_followup_01 | followups_communication | typo_en | quotes go out then nobody ever folows up | | | |
| rc_intake_01 | lead_intake | non_native_en | People come to website but never become real customers. What can help? | | | |
| rc_support_01 | customer_support | standard_en | Our customers email the same five questions every week. | | | |
| rc_docs_01 | document_automation | informal_us | we rewrite the same intake packet for every new client ugh | | | |
| rc_invoice_01 | quotes_invoicing | standard_en | Can estimates turn into invoices without retyping everything? | | | |
| rc_sync_01 | data_sync | standard_en | We type customer details into three apps every time. | | | |
| rc_coord_01 | employee_coordination | standard_en | Office and field staff disagree about who owns each open job. | | | |
| rc_inv_01 | inventory | standard_en | We keep running short on parts mid-job. | | | |
| rc_web_01 | website_digital_ops | informal_us | pretty website but the office never sees what comes in | | | |
| rc_int_01 | integrations | standard_en | We already have tools. Can Fikiri connect to what we use today? | | | |
| rc_disc_01 | business_discovery | jamaican_influenced | Tings inefficient but mi nuh know whey fi start. | | | Known live fallback today |
| rc_pay_01 | payments_billing | standard_en | Clients ignore invoices until we chase them manually. | | | |
| rc_multi_01 | lead_intake | standard_en | Website forms, no follow-up, and I can't see who is a real opportunity. | | | |
| rc_contrast_delete_01 | customer_management | standard_en | Can you wipe our entire customer database automatically every night? | | | Contrast / refuse |
| rc_handoff_01 | business_discovery | standard_en | This is getting specific — can I talk to someone on your team? | | | Expect contact |
| rc_logistics_01 | scheduling_dispatch | standard_en | I run a small courier service. Drivers clash on routes and customers call when we're late. | | | Known live fallback today |
| rc_amb_01 | business_discovery | informal_us | idk things feel stuck | | | Known live fallback today |
| rc_report_jobs_01 | reporting_analytics | standard_en | Which types of jobs actually make us money after costs? | | | |
| rc_crm_01 | customer_management | slang | yall got something like a crm for a tiny team? | | | |
| rc_simple_en_01 | business_discovery | simplified_en | Please explain in simple English how you help small businesses. | | | |
| rc_hipaa_01 | customer_support | standard_en | Are you HIPAA certified for patient email? | | | Must not claim certification |

---

## 4. Release gate

### Regression (company-chatbot pack)

| Check | Result |
|---|---|
| Expanded chatbot regression | **209 passed** (golden, BNR, FCRB, modes, capabilities, scenarios, messy language, mixed-scope, intake, guards, deterministic eval, site API) |
| Legacy golden suite | **103 cases** still gated; suite asserts count + pass floors |
| Unsupported capability guarantees (BNR floors) | **0** unsupported-claim rate on program tests |
| Pricing / Gmail-Outlook / intake / human handoff | Covered by critical scenarios + mode/conversational suites; **passing** in last run |
| Deploy | **Not performed** |

### Version identity (critical)

| Item | Value |
|---|---|
| Git HEAD (committed) | `681b62e9b6c52fb62474acabb49bd5af799b324d` — *Route engagement explanations to grounded answers, not intake.* |
| BNR implementation | **Present in working tree; not committed** |
| Exact releasable commit for BNR | **None yet** — owner must approve claims, then a dedicated commit/tag must be created before any deploy |
| Branch at prepare time | `fix/frontend-advisory-bumps` tracking `origin/main` (local dirty) |

**Do not treat HEAD alone as the BNR release artifact.**

### Rollback (when a BNR commit eventually ships)

1. Revert the BNR release commit(s) on the deployed branch (`git revert <bnr-commit>…`).  
2. Redeploy previous known-good backend artifact.  
3. Confirm golden retrieval eval (103) + critical scenarios still pass.  
4. If only config/data shipped: restore prior `fikiri_business_need_taxonomy.json` / `fikiri_capability_map.json` and restart workers.  
5. Site chat has no separate feature flag in this slice — rollback = code/data revert + redeploy.

### Hard blockers before deploy

- [ ] Owner completes matrix APPROVE/EDIT/BLOCK (especially scheduling, payment-status, inventory, booking-bundle)  
- [ ] Independent labels on 24 RC cases  
- [ ] BNR changes committed and tagged as the release version  
- [ ] Re-run full chatbot regression on that exact commit  
- [ ] Explicit owner “deploy approved”  

---

## Sign-off

| Role | Decision | Date | Signature / initials |
|---|---|---|---|
| Owner — claims | **Approve** (blanket approval to ship) | 2026-11-18 | Owner (chat) |
| Owner — release labels | Deferred — RC remains for post-ship independent labeling | 2026-11-18 | |
| Owner — deploy | **Deploy/update approved** + keep transcript collection for study/training | 2026-11-18 | Owner (chat) |

**Post-approval actions:** commit BNR + transcript study meta → push `main` → Render auto-deploy → confirm `FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS=1`.
