# Fikiri Site Bot — Phase 6d Handoff (Transcript Miss Review)

## Goal

Close the improvement loop without auto-mutating production KB:

```
production chat → transcript capture → miss detection → alias/eval proposal
→ human approval → Cursor patch → tests → deploy
```

API-only. No frontend admin UI. No LLM. No automatic KB edits.

## Miss signals (deterministic)

| Signal | Trigger |
|--------|---------|
| `ungrounded` | `grounded=false` on assistant turn |
| `low_confidence` | confidence below `FIKIRI_SITE_BOT_GROUNDING_MIN_SCORE` |
| `fallback_used` | mode `fallback` |
| `handoff_after_fallback` | fallback + handoff applicable |
| `user_frustration_followup` | next user message matches guard frustration patterns |
| `user_correction_followup` | “that’s not what I meant”, etc. |
| `repeated_clarification` | generic fallback + repeated user phrase |
| `low_retrieval_score` | replay `retrieve()` below grounding threshold |
| `warm_lead_ungrounded` / `hot_lead_ungrounded` | warm/hot tier without grounded answer |

Priority: `critical` (warm/hot miss) → `high` → `medium` → `low`.

## Admin API

All routes require staff auth (same as transcript read API).

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/admin/site-chat/misses` | List likely misses (`limit`, `offset`, `min_priority`) |
| GET | `/api/admin/site-chat/misses/<session_id>:<turn>` | Miss detail + alias proposal |
| GET | `/api/admin/site-chat/misses/<session_id>:<turn>/export` | Copy-friendly Cursor patch (`format=cursor`) |

Miss ID format: `site_<uuid>:<turn_index>` (e.g. `site_abc123:1`).

## Proposal object

Each proposal includes:

- `suggested_alias` — normalized visitor phrase
- `suggested_service_families` — from retrieval replay
- `suggested_chunk_ids` — top retrieval chunks
- `suggested_eval_case` — YAML-ready eval snippet
- `cursor_patch` — paste into Cursor for human-reviewed patch
- `requires_human_approval: true` (always)

**Nothing is written to KB automatically.**

## Operational workflow

1. Enable transcripts: `FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS=1`
2. Review misses: `GET /api/admin/site-chat/misses?min_priority=high`
3. Export patch: `GET /api/admin/site-chat/misses/<id>/export`
4. Paste into Cursor, approve alias + eval case manually
5. Run retrieval eval + full site-bot tests
6. Deploy

## Files

- `company_chatbot/miss_review.py` — detection, proposals, cursor export
- `routes/admin_site_chat_api.py` — admin endpoints
- `tests/test_company_chatbot_miss_review.py`
- `tests/test_admin_site_chat_api.py` (miss endpoints)

## Tests

```bash
FIKIRI_SITE_BOT_TEST_MODE=1 python3 -m pytest \
  tests/test_company_chatbot_miss_review.py \
  tests/test_admin_site_chat_api.py -q
```

## Out of scope

- Frontend admin page
- Auto KB mutation
- LLM proposal generation
- Tenant chatbot changes
