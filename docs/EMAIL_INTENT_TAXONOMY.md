# Email intent taxonomy (AI Email Assistant)

## One canonical classification path

All production entry points must use **`MinimalAIEmailAssistant.analyze_incoming_email()`** (directly or via `classify_email_intent`, which delegates to it).

| Entry point | `classification_source` |
|-------------|-------------------------|
| Gmail/Outlook mailbox sync (`pipeline.orchestrate_incoming`) | `mailbox_sync` |
| Manual Analyze API (`POST /api/ai/analyze-email`) | `manual_api` |
| Generate reply API (when analysis not supplied) | `manual_api` |
| Legacy `classify_email_intent()` | `legacy_wrapper` |
| LLM success | `v2_ai` |
| Heuristic / AI failure fallback | `v2_fallback` |

There is **no separate 5-intent LLM prompt** on the primary path.

### Response contract (v2 + legacy aliases)

Consumers should prefer:

- `intent` — canonical taxonomy id (e.g. `pricing_request`)
- `legacy_intent` — mapped legacy label (e.g. `lead_inquiry`) for old UI code
- `confidence_score`, `lead_score`, `urgency_score`, `business_value_score`
- `sender`, `extracted_details`, `recommended_action_detail`, `reply_guidance`
- `reasoning_summary`, `classification_source`

Legacy alias keys still present: `confidence`, `urgency`, `suggested_action`, `recommended_action`.

### `classify_email_intent` compatibility

Still callable but runs the same v2 analysis. Returns the **full** analysis object (not a slim 4-field dict). Old code reading `intent` alone should switch to `legacy_intent` if they expect `lead_inquiry`-style values; new code should use canonical `intent`.

### Reply generation

Classify **once** in `orchestrate_incoming`, then pass `_analysis` on the parsed email into auto-reply. See [EMAIL_REPLY_GENERATION.md](EMAIL_REPLY_GENERATION.md).

`generate_response(..., analysis=...)` uses v2 fields (tone, requested service, pain points, next action) and returns `analysis.suggested_reply` when already present (no second classify / no reply LLM).

## Extending intents

1. Add the new ID to `PRIMARY_EMAIL_INTENTS` in `core/ai/email_intent_taxonomy.py`.
2. Add aliases to `LEGACY_INTENT_MAP` if models may return shorthand labels.
3. Update routing sets (`AUTO_REPLY_INTENTS`, `CRM_UPSERT_INTENTS`, `HIGH_RISK_INTENTS`) as needed.
4. Add a regex hint in `email_automation/email_intent_classifier.py` `build_rule_hints()` if deterministic pre-filtering helps.
5. Extend optional fields on `BusinessEmailAnalysisSchema` in `core/ai/schemas.py` (additive only).
6. Add tests in `tests/test_email_intent_classifier.py`.

## Client customization

Per-user settings load from:

- `users.business_name`, `users.industry`, `users.metadata.email_assistant`
- `user_services` row `ai-assistant` → `settings` JSON keys:
  - `responseTone`, `servicesOffered`, `highValueKeywords`, `lowValueKeywords`
  - `customIntentLabels`, `escalationRules`, `leadScoringWeights`
- Fallback file: `data/business_profile.json`

Loader: `core/client_email_config.py` → `load_client_email_config(user_id)`.

## Classification pipeline (layered)

```
Gmail/Outlook sync → parser.py → pipeline.orchestrate_incoming
  → run_inbound_email_workflow (CRM upsert)
  → ai_assistant.analyze_incoming_email
       1. preprocess_email_metadata()
       2. build_rule_hints(client_config)
       3. LLM (BusinessEmailAnalysisSchema) via LLMRouter
       4. normalize_business_analysis()
       5. evaluate_email_action_policy()
```

Fallback (AI off / invalid JSON): `classify_with_fallback()` — rules only, always `needs_human_review=true`.

## Backward compatibility

- `intent` — canonical taxonomy ID (v2).
- `legacy_intent` — maps to pre-v2 strings for older dashboards/tests.
- Top-level `confidence`, `urgency`, `business_value` retained for existing consumers.
