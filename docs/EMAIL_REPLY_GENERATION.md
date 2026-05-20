# Email reply generation (mailbox sync)

## Principle: classify once, reply from analysis

Mailbox automation runs **one** v2 analysis per message in `pipeline.orchestrate_incoming` → `analyze_incoming_email`. That object is attached to the parsed email as `_analysis` before `MinimalEmailActions.process_email`.

Reply text is produced by `actions._generate_reply_content` → `ai_assistant.generate_reply_with_metadata`, which **must not** call `classify_email_intent` again.

## Reply generation modes

| Mode | When | Extra LLM call? | Pipeline `ai_responses` +1 |
|------|------|-----------------|----------------------------|
| `reused_suggested_reply` | `analysis.suggested_reply` is non-empty | No | No (analyze already counted) |
| `llm_with_analysis_context` | Analysis present, no draft; reply LLM uses intent/tone/pain points | Yes | Yes (when gate on) |
| `llm_no_analysis` | No analysis on parsed email | Yes | Yes (when gate on) |
| `template_fallback` | AI disabled or LLM failure | No | No |
| `assistant_disabled` | AI off | No | No |

Structured log event: `reply_generation.completed` with `reply_generation_mode` and `llm_called`.

## Token / cost savings

- Reusing `suggested_reply` avoids a second full reply LLM call (~300–800 tokens typical).
- When `FIKIRI_EMAIL_PIPELINE_AI_GATE=1`, only **analyze** increments usage for reuse path; reply LLM paths increment once more.

## Manual API (`POST /api/ai/generate-reply`)

- Pass optional `analysis` in the body to skip re-analysis.
- Response includes `{ reply, analysis }` when analysis was run in-request.
- Budget/`ai_responses` usage mirrors mailbox sync: analyze counts once when run in-request; reply LLM counts once unless mode is `reused_suggested_reply`, `template_fallback`, or `assistant_disabled`.

## Extending

Add fields to v2 analysis only; do not add parallel classification prompts. If reply needs new context, extend `analyze_incoming_email` output and pass through `_analysis` on parsed emails.
