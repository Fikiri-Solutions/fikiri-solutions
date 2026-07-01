# Fikiri Site Bot Phase 2 Handoff

**Status:** Complete (KB + grounding)  
**Prior:** [FIKIRI_SITE_BOT_PHASE_1_HANDOFF.md](./FIKIRI_SITE_BOT_PHASE_1_HANDOFF.md)  
**Rules:** [FIKIRI_SITE_BOT_ENGINEERING_RULES.md](./FIKIRI_SITE_BOT_ENGINEERING_RULES.md)

## What Phase 2 Added

- Curated KB under `data/company_chatbot/`
  - `fikiri_kb_chunks.jsonl` — evidence snippets (public site sources)
  - `fikiri_company_profile.json` — contact + forbidden-unless-in-KB terms
- `company_chatbot/retrieval.py` — deterministic token-overlap retrieval (no vectors, no LLM)
- `company_chatbot/grounding.py` — threshold gate, sensitive-topic block, evidence-only answers
- `answer` mode wired through orchestrator (evidence-first)
- Response fields: `grounded`, `confidence`, `sources`
- 10 critical YAML scenarios in `tests/company_chatbot_scenarios/critical.yaml`

## Still Not in Scope

- No frontend widget
- No database session persistence
- No CRM lead persistence
- No OpenAI / LLM polish (`FIKIRI_SITE_BOT_LLM_POLISH` remains off)

## Env

| Variable | Default | Purpose |
|----------|---------|---------|
| `FIKIRI_SITE_BOT_TEST_MODE` | — | `1` = zero model calls |
| `FIKIRI_SITE_BOT_KB_DIR` | `data/company_chatbot` | KB artifact directory |
| `FIKIRI_SITE_BOT_GROUNDING_MIN_SCORE` | `0.25` | Minimum retrieval score to answer |
| `FIKIRI_SITE_BOT_RETRIEVAL_TOP_K` | `3` | Chunks passed to grounding |

## Tests

```bash
FIKIRI_SITE_BOT_TEST_MODE=1 python3 -m pytest \
  tests/test_company_chatbot_modes.py \
  tests/test_company_chatbot_grounding.py \
  tests/test_company_chatbot_scenarios.py \
  tests/test_site_chatbot_api.py -q
```

Current result: **37 passed**

## Phase 2 Acceptance

| Requirement | Status |
|-------------|--------|
| Curated KB files | Passed |
| `retrieval.py` | Passed |
| `grounding.py` | Passed |
| Evidence-first `answer` mode | Passed |
| 10 critical scenario tests | Passed |
| No widget / DB / lead persistence | Passed |
| Tenant chatbot untouched | Passed |

## Next Phase

Phase 3 complete — see [FIKIRI_SITE_BOT_PHASE_3_HANDOFF.md](./FIKIRI_SITE_BOT_PHASE_3_HANDOFF.md).

**Phase 4 (suggested)** — frontend widget only.
