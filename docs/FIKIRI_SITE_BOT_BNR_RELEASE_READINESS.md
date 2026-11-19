# Fikiri Business-Need Recognition — Release Readiness

**Verdict: architecture approved directionally; NOT ready for production deploy without owner approval.**  
**Date:** 2026-11-18

## What is preserved

- 15-category business-need taxonomy  
- Capability map + bridge composer  
- 103-case golden retrieval suite (frozen)  
- BNR 150 (120/30) + FCRB 50 benchmarks (labels `draft_unvalidated`)  
- Fresh release candidate set: `tests/company_chatbot_bnr_release_candidate.yaml` (**do not tune on it**)

## Phase results

### Phase 1 — Response quality (prior 30 holdout)

- 28 `need_recognized_useful`, 2 `useful_without_need_id`, **0** `generic_consult`  
- Need recognition **93.3%**; draft auto-pass **100%**; fallback **0%**  
- Detail: `docs/FIKIRI_SITE_BOT_BNR_HOLDOUT_QUALITY_REVIEW.md`

### Phase 2 — Claim audit

- Categories classified verified / custom_discovery / unsupported  
- Uncertain claims flagged for owner: payment-status reporting, scheduling custom scope, inventory limitation language  
- Detail: `docs/FIKIRI_SITE_BOT_BNR_CLAIM_AUDIT.md` + owner sheet

### Phase 3 — Two concept misses

| Miss | Cause | Fix |
|---|---|---|
| Restaurant order tracking | Need/phrase gap + wrong bundle | Reusable CRM order-history concepts; bundle bleed guards; taxonomy claims in bridge |
| Bakery who-pays | Need/phrase gap | Reusable reporting/payment-status concepts; Workflow Audit path |

Also fixed: `profit`⊂`nonprofit` false positive via token-boundary/stem matching.

### Phase 4 — Human review artifacts

- Owner claim matrix: `docs/FIKIRI_SITE_BOT_BNR_OWNER_REVIEW.md`  
- Holdout quality table + JSON dump  
- Automated labels **must not** be represented as independently verified

### Phase 5 — Independent release evaluation

- Fresh 24-case candidate prepared  
- **Blocked on independent labeling** before scoring  
- Prior 30 holdout = historical / observed evidence only

### Phase 6 — Regression & deploy assessment

Ran company-chatbot regression pack (209 passed), including golden retrieval, BNR/FCRB, modes, capabilities, scenarios (incl. workflow-audit intake + email decline), mixed-scope, messy language, intake, guards, deterministic eval, site API.

Confirmations:
- Original 103 golden cases still gated by suite tests  
- Gmail/Outlook / topic-switch covered by existing conversational/messy/mode suites  
- Pricing / human-help / contact-intake scenarios still passing  
- Unsupported-claim rate on BNR remain 0 in program test floors  

**Do not deploy without owner approval.**

## Target customer-style response (milestone)

Preferred shape (owner):

> It sounds like you're trying to track which customers have outstanding balances and which accounts have paid. Fikiri builds custom CRM and business workflow solutions that may help with that. We'd need to understand your current payment and accounting systems before recommending an approach.

Current bakery holdout reply:

> That sounds like a reporting and analytics problem… Seeing which accounts have paid vs outstanding is often a CRM + reporting workflow scoped after discovery… Workflow Audit…

Directionally aligned with the preferred customer-style response; final copy polish still owner-optional.

## Unresolved risks

1. Labels remain draft / provisional  
2. Prior holdout is no longer pristine  
3. Release candidate unlabeled  
4. DEV need recognition (~82.5%) still trails DEV auto-pass (100%) — same useful-vs-exact-id gap  
5. Some answers still slightly bundle-generic vs the preferred CRM/receivables wording  
6. Claim language needs owner APPROVE/EDIT/BLOCK

## Deployment readiness

| Gate | Status |
|---|---|
| Deterministic BNR + bridge implemented | Done (not deployed) |
| Golden 103 intact | Confirm in regression run |
| Owner claim approval | **Open** |
| Independent release labels | **Open** |
| Production deploy | **Blocked — needs owner approval** |
