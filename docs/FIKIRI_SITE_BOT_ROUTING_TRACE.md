# Fikiri Site Bot — Routing Trace

## Purpose

Inline routing trace records **why** a visitor message entered a given handler path. It is observability only: tracing must not change routing behavior, thresholds, or responses.

Use it to answer:

> Why did this message enter this handler?

## Core invariant

Every trace field is captured from the **same function call** that produced the user-visible response.

- Do **not** rerun `detect_mode()`, `detect_needs()`, `retrieve()`, or `apply_grounding()` after the response is produced.
- Post-hoc replay (for example `miss_review.py` re-calling `retrieve()`) is useful for triage but is **not ground truth**.

Tracing must never add detection or retrieval calls when the feature flag is off.

## Inline trace vs miss-review replay

| Mechanism | When | Trust level |
|-----------|------|-------------|
| **Inline `routing_trace`** | During `handle_message()` | Ground truth |
| **`miss_review` replay** | After transcript stored | Hypothesis / triage only |

Miss review proposes vocabulary patches. Inline trace diagnoses the actual turn.

## Pipeline order (current)

```
guard
  → intake interrupt mode check? (detect_mode)
  → mode (detect_mode)
  → intake start? / handler dispatch
  → finalize (lead scoring, repeat guard)
  → outcome recorded on MessageResult
```

Later slices may add `needs`, `retrieval`, `grounding`, and `rescue` sections without changing this order.

## Schema v1

```json
{
  "schema_version": "v1",
  "path": ["guard", "mode", "outcome"],
  "guard": {
    "attempted": true,
    "triggered": false,
    "reason": null
  },
  "mode": {
    "attempted": true,
    "detected": "fallback",
    "matched_rule": null,
    "previous_query_used": false
  },
  "outcome": {
    "mode": "answer",
    "grounded": true,
    "confidence": 0.62
  }
}
```

### Field rules

- **JSON-safe only** — no regex objects, message bodies, tokens, credentials, or KB content.
- **`mode.detected`** — result of `detect_mode()` for this turn. Do not overwrite after rescue or handler upgrades.
- **`outcome.mode`** — final `MessageResult.mode` after handlers and finalize.
- **`matched_rule`** — stable rule identifier from `modes.py` (for example `product_pricing_integrations`, `business_need_bridge`, `empty_message`), or `null` when no rule matched.
- **`path`** — ordered steps executed this turn. Prefer presence checks over brittle exact-sequence assertions in tests.

### Mode rule identifiers (v1)

| `matched_rule` | Mode |
|----------------|------|
| `contact_request` | `contact` |
| `workflow_audit_request` | `workflow_audit` |
| `consulting_request` | `consulting` |
| `explore_fit` | `explore_fit` |
| `compliance_boundary` | `answer` |
| `product_pricing_integrations` | `answer` |
| `mixed_scope_answer` | `answer` |
| `vague_office_pain` | `answer` |
| `email_assistant_product` | `answer` |
| `business_need_bridge` | `answer` (capability bridge inside `detect_mode`) |
| `empty_message` | `fallback` |
| `null` | `fallback` (no rule matched) |

## Exposure policy

Environment flag:

```text
FIKIRI_SITE_BOT_ROUTING_TRACE=1
```

Default: **disabled**.

| Flag | Behavior |
|------|----------|
| Off | No `routing_trace` in serialized responses; no extra work |
| On (local / tests) | `routing_trace` included in `MessageResult.to_dict()` |

- Do not expose trace in the production marketing widget by default.
- Transcript persistence and admin UI for trace are deferred to later slices.

## Debugging workflow

For a failed phrase, inspect in order:

1. **Guard** — blocked by turn cap, frustration, repeat, or low-information intake?
2. **Mode** — `detected`, `matched_rule`, `previous_query_used`
3. **Outcome** — final mode vs routed mode (rescue may differ; rescue tracing deferred)

Patch the **smallest canonical layer** that failed. Add one regression test at that layer.

| Failure point | Smallest likely correction |
|---------------|----------------------------|
| Guard misfires | Narrow guard condition |
| Mode routes to fallback | One mode rule or bridge adjustment |
| Outcome differs from detected mode | Handler/rescue behavior (trace rescue in later slice) |

Do not add the same phrase to every layer without tracing.

## Implementation slices

1. **This document + v1 schema** — guard, mode, outcome (current)
2. Needs trace + `matched_phrases`
3. Retrieval top chunks (bounded, no score components initially)
4. Grounding accept/reject reason
5. Rescue path fields
6. Transcript persistence
7. Miss review reads stored trace instead of replaying retrieval

## Tests

See `tests/test_company_chatbot_routing_trace.py`.

When the flag is off, existing response shape must remain unchanged.
