# Fikiri Site Bot Phase 3 Handoff

**Status:** Complete (intake + guards)  
**Prior:** [FIKIRI_SITE_BOT_PHASE_2_HANDOFF.md](./FIKIRI_SITE_BOT_PHASE_2_HANDOFF.md)  
**Rules:** [FIKIRI_SITE_BOT_ENGINEERING_RULES.md](./FIKIRI_SITE_BOT_ENGINEERING_RULES.md)

## What Phase 3 Added

- `company_chatbot/intake.py` — 4 core slots (`industry`, `main_pain`, `timeline`, `contact_email`), optional `name` / `business_name`, one question per turn
- `company_chatbot/guards.py` — turn cap (12), frustration phrases, low-info during intake, repeat-response block (no 3rd identical reply)
- `orchestrator.py` — intake state on sessions, FAQ/contact interrupts intake, guard handoff exits
- Response schema: optional `intake` object (`active`, `complete`, `next_slot`, `slots`, `filled_core_count`)
- Scenario suite expanded to **21** cases in `tests/company_chatbot_scenarios/critical.yaml`
- Unit tests: `test_company_chatbot_intake.py`, `test_company_chatbot_guards.py`

## Intake Rules (locked)

**Starts only for modes:** `explore_fit`, `workflow_audit`, `consulting` (plus explicit help/quote phrases in `modes.py`).

**Does not start for:** FAQ/pricing/product questions (`answer` mode).

**Completes when:** 3+ core slots filled (email optional if declined).

**On frustration / turn cap / repeat:** summarize + `/intake` handoff.

## Still Not in Scope

- No frontend widget
- No database persistence
- No CRM / email / Slack delivery
- No OpenAI / LLM polish
- No vector retrieval

## Tests

```bash
FIKIRI_SITE_BOT_TEST_MODE=1 python3 -m pytest \
  tests/test_company_chatbot_modes.py \
  tests/test_company_chatbot_grounding.py \
  tests/test_company_chatbot_intake.py \
  tests/test_company_chatbot_guards.py \
  tests/test_company_chatbot_scenarios.py \
  tests/test_site_chatbot_api.py -q
```

Current result: **62 passed**

## Phase 3 Acceptance

| Requirement | Status |
|-------------|--------|
| Short deterministic intake | Passed |
| Real guards (turn/repeat/frustration/low-info) | Passed |
| FAQ users not interrogated | Passed |
| One question per intake turn | Passed |
| Handoff on complete / guard exit | Passed |
| 21 scenario tests | Passed |
| Tenant chatbot untouched | Passed |
| No widget/DB/CRM/model calls | Passed |

## Next Phase

Phase 4 complete — see [FIKIRI_SITE_BOT_PHASE_4_HANDOFF.md](./FIKIRI_SITE_BOT_PHASE_4_HANDOFF.md).

**Phase 5 (suggested):** DB persistence + CRM + notifications — explicit scope only.
