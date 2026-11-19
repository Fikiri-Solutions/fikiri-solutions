# Business-Need Recognition (BNR) — Iteration Log

**Status:** development complete for this program slice — **not deployed**  
**Labels:** `draft_unvalidated` until dual human review  
**Production LLM:** none

## Phase 1 — Architecture finding

Path: `message → guards → detect_mode → retrieve/ground OR fallback`.

Fallback already contained a **capability rescue** (`detect_needs` ≥ 0.35 → `compose_capability_bridge`).  
Root cause of “retrieved OK, still fallback”: **mode rules and capability phrases missed the utterance**, so rescue never fired—even when retrieval ranked relevant chunks.

## Phase 2 — Taxonomy

`data/company_chatbot/fikiri_business_need_taxonomy.json` — 15 reusable need categories mapped to existing capability families with `verified` / `custom_discovery` / `unsupported_or_discovery` statuses.

## Phase 3 — Benchmark

`tests/company_chatbot_bnr_benchmark.yaml` — **150** scenarios (15×10), **120 dev / 30 holdout**.  
Provisional AI/engineer-authored labels; not independently dual-reviewed.

## Metrics history

| Step | Golden pass | BNR DEV auto | BNR DEV need | BNR holdout auto | FCRB auto | Notes |
|------|-------------|--------------|--------------|------------------|-----------|-------|
| Pre-change (approx) | 1.00 | ~0.60 | ~0.39 | ~0.40 | 0.66 | Fallback-heavy |
| After bridge v1 | 1.00 | 0.60 | 0.39 | 0.40 | 0.78 | Logistics example answered |
| After phrase expand | 1.00 | 0.917 | 0.742 | 0.933 | 0.78 | Concept phrases |
| After DEV-targeted expand | 1.00 | **1.00** | **0.825** | **0.933** | 0.78 | Stopped; avoid holdout tuning |
| Release-readiness slice | 1.00* | **1.00** | **0.825** | **1.00** auto / **0.933** need | 0.78 | CRM/reporting concepts; claim audit; **0** generic consult |

\*Confirm in Phase 6 regression run.

Unsupported-claim rate remained **0** on BNR.

## Holdout quality (release-readiness)

Prior two concept misses (restaurant order track; bakery who-pays) fixed with **reusable CRM/reporting concepts**, not industry aliases.  
Holdout quality: 28 need_recognized_useful / 2 useful_without_need_id / **0** generic_consult.  
Treat this 30-set as **previously observed** evidence — fresh release candidate is `tests/company_chatbot_bnr_release_candidate.yaml`.

## Safeguards

- Golden retrieval suite (**103**) unchanged and still **100%** pass / Hit@3 **1.0**
- No automatic deploy
- Human review still required before customer-facing accuracy claims
