# Mixed-Scope QA & Tuning Loop

## Key rule (do not skip)

When the bot misses a real client phrase:

1. **Add phrase to capability map** if it describes a need/pain (`fikiri_capability_map.json` → family or capability `client_phrases`).
2. **Add service-family relationship** if the scope is mixed (`related_families` or bundle `family_ids`).
3. **Add or adjust KB chunk** only if the **factual answer** is missing.
4. **Add eval case** (`company_chatbot_mixed_scope_qa.yaml` or `company_chatbot_capability_eval.yaml`).
5. **Run tests.**

Do **not** stuff random keywords into KB aliases. That turns the KB into a junk drawer.

## QA set

**File:** `tests/company_chatbot_mixed_scope_qa.yaml`  
**Count:** 35 mixed-scope conversations (single- and multi-turn)

Examples covered:

- Website + lead tracking
- Book and pay online
- Email + follow-up connected
- Forms but nobody follows up
- Chatbot + capture leads
- One small workflow fixed
- “Office is messy” / not sure what I need
- Multi-turn: Gmail after email assistant; pricing interrupt during audit

**Tests:** `tests/test_company_chatbot_mixed_scope_qa.py`

- Full bot path (`handle_message`) — mode, grounded, `must_include`
- Needs detection on final turn (`detect_needs`)
- Aggregate baseline (informational): family ≥ 90%, bundle ≥ 85%, grounded + mode tracked in `test_mixed_scope_qa_baseline_report`

**Mode routing (Phase 6e follow-up):** Valid business-need phrases that score on the capability map (`detect_needs` confidence ≥ 0.35) route to `answer` mode via `modes._needs_imply_answer()` — avoids stuffing one-off regex for every mixed-scope phrase.

```bash
FIKIRI_SITE_BOT_TEST_MODE=1 python3 -m pytest tests/test_company_chatbot_mixed_scope_qa.py -s -q
FIKIRI_SITE_BOT_TEST_MODE=1 python3 -m pytest tests/test_company_chatbot_messy_language_variations.py -s -q
```

**Messy-language matrix:** `tests/company_chatbot_messy_language_variations.yaml` — 30 cases (6 seeds × original/short/simple/long/complex). Every case must produce a sales-ready `lead_assessment.synopsis` even when routing is imperfect. Fallback turns run `detect_needs` rescue when confidence ≥ 0.35.

Failures print **tuning candidates** — use those with Phase 6d miss review, then patch the capability map.

## Production tuning loop (6d → 6e)

```
1. FIKIRI_SITE_BOT_PERSIST_TRANSCRIPTS=1 in staging
2. GET /api/admin/site-chat/misses?min_priority=high
3. GET /api/admin/site-chat/misses/<id>/export  → Cursor patch
4. Human approves: edit fikiri_capability_map.json (not KB first)
5. Append case to company_chatbot_mixed_scope_qa.yaml if new phrasing
6. pytest tests/test_company_chatbot_mixed_scope_qa.py
   tests/test_company_chatbot_capabilities.py
   tests/test_company_chatbot_retrieval_eval.py
7. Deploy
```

## When to touch the KB

Only when verified marketing copy is missing — e.g. a new service line, pricing fact, or boundary the site actually publishes. Capability map handles **meaning**; KB handles **evidence**.
