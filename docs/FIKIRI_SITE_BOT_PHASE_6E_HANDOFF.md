# Fikiri Site Bot — Phase 6e Handoff (Capability Map)

## Goal

Map messy client language through **pain → capability → service family → bundle → KB chunks**, not a single product keyword.

```
client phrase → capabilities → families → suggested bundle → grounded chunks
```

No LLM. No auto KB edits.

## Three layers (`data/company_chatbot/fikiri_capability_map.json`)

1. **Service families** (9) — how clients think: `forms_and_intake`, `crm_and_lead_tracking`, `email_and_inbox_automation`, etc.
2. **Capabilities** (10) — mix-and-match: capture lead, send follow-up, update CRM, book appointment, …
3. **Bundles** (5) — solution paths: Lead Intake System, Email Workflow Assistant, Workflow Audit, …

Each family entry includes:

- `client_phrases` (attached to meaning, not bare keywords)
- `capabilities`
- `related_families`
- `kb_chunk_ids`
- `legacy_family_ids` (bridges Phase 6c eval families)
- optional `disambiguation_question`

## Detection API (`company_chatbot/capabilities.py`)

`detect_needs(query, previous_query=..., effective_query=...)` returns:

```json
{
  "detected_families": ["website_and_landing_pages", "forms_and_intake", "crm_and_lead_tracking"],
  "detected_capabilities": ["capture lead", "update CRM"],
  "suggested_bundle": "lead_intake_system",
  "suggested_bundle_label": "Lead Intake System",
  "confidence": 0.86,
  "kb_chunk_ids": ["workflow_inquiry_leak", "product_crm_overview", "..."],
  "disambiguation_question": null
}
```

## Integration

- **Retrieval** — capability map boosts chunks via `kb_chunk_ids`; `RetrievalResult.needs` carries detection payload
- **Grounding** — multi-family queries use `capability_bridge` responses (mix + bundle summary + KB evidence + next step)
- **Phase 6c families** — still used; capability map adds `legacy_family_ids` mapping for backward compatibility

## Eval

- `tests/company_chatbot_capability_eval.yaml` — 20 multi-need cases
- `tests/test_company_chatbot_capabilities.py` — family match ≥ 90%, bundle match ≥ 75%

## Improvement loop (with 6d)

```
transcript miss → admin proposal → human adds phrase to capability map (not random KB keywords)
→ eval → deploy
```

Prefer editing `fikiri_capability_map.json` client_phrases on the right family/capability before adding orphan KB aliases.

## Tests

```bash
FIKIRI_SITE_BOT_TEST_MODE=1 python3 -m pytest \
  tests/test_company_chatbot_capabilities.py \
  tests/test_company_chatbot_retrieval_eval.py -q
```

## Files

- `company_chatbot/capabilities.py` (new)
- `data/company_chatbot/fikiri_capability_map.json` (new)
- `company_chatbot/retrieval.py` (needs payload + capability boost)
- `company_chatbot/grounding.py` (capability_bridge)
- `tests/company_chatbot_capability_eval.yaml`
- `tests/test_company_chatbot_capabilities.py`
