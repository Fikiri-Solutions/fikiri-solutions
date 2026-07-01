# Fikiri Site Bot Phase 1 Handoff

**Status:** Accepted (Phase 1 complete)  
**Engineering rules:** [FIKIRI_SITE_BOT_ENGINEERING_RULES.md](./FIKIRI_SITE_BOT_ENGINEERING_RULES.md)

## Current State

- Backend skeleton exists under `company_chatbot/`.
- Site routes exist under `routes/site_chatbot_api.py`.
- Registered in `app.py`.
- No frontend widget yet.
- No KB retrieval yet.
- No database persistence yet (in-memory sessions only).
- No OpenAI/model calls.

## API

- `POST /api/site/chat/session/start` — returns `session_id`, `welcome`, `schema_version: v1`
- `POST /api/site/chat/message` — body: `session_id`, `message`; returns `mode`, `response`, `handoff`, `lead_intent`, `schema_version: v1`

No public chatbot API key required.

## Locked Decisions (Phase 1)

| Topic | Decision |
|-------|----------|
| Handoff | Metadata only: primary `in_widget_form` (later), secondary `/intake` or `/contact` |
| LLM | Deterministic until scenario tests pass; then polish behind `FIKIRI_SITE_BOT_LLM_POLISH` |
| Leads | `lead_intent` schema in responses only; CRM persistence in a later phase |

## Design Rules

- Separate from tenant chatbot product.
- Do not touch `core/public_chatbot_api.py`.
- Do not touch `core/chatbot_*.py`.
- Do not touch `frontend/**` before widget phase.
- Deterministic by default.
- LLM polish remains off until scenario tests pass.
- Use dispatch maps and modular functions, not giant if/elif chains.

## Env

| Variable | Purpose |
|----------|---------|
| `FIKIRI_SITE_BOT_TEST_MODE=1` | Guarantees zero OpenAI/model calls |
| `FIKIRI_SITE_BOT_LLM_POLISH` | Off by default; enable only after scenarios pass |

## Tests

```bash
FIKIRI_SITE_BOT_TEST_MODE=1 python3 -m pytest tests/test_company_chatbot_modes.py tests/test_site_chatbot_api.py -q
```

Current result: **21 passed**

## Phase 1 Acceptance

| Requirement | Status |
|-------------|--------|
| Separate `company_chatbot/` module | Passed |
| `/api/site/chat/session/start` | Passed |
| `/api/site/chat/message` | Passed |
| No API key required | Passed |
| No OpenAI/model calls | Passed |
| No KB/DB/frontend yet | Passed |
| Handler dispatch map | Passed |
| In-memory sessions only | Passed (skeleton) |
| Test mode supported | Passed |
| Scoped tests passed | 21 passed |
| Tenant chatbot untouched | Passed |

## Next Phase

Phase 2 complete — see [FIKIRI_SITE_BOT_PHASE_2_HANDOFF.md](./FIKIRI_SITE_BOT_PHASE_2_HANDOFF.md).  
Phase 3 complete — see [FIKIRI_SITE_BOT_PHASE_3_HANDOFF.md](./FIKIRI_SITE_BOT_PHASE_3_HANDOFF.md).
