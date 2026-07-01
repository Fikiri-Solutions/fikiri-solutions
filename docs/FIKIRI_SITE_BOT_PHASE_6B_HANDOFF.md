# Fikiri Site Bot — Phase 6b Handoff (Retrieval Precision)

## Goal

Improve deterministic KB retrieval so answer-mode questions reach the right 1–3 chunks before grounding, without vectors or LLM calls.

## Targets

| Metric | Target | Result |
|--------|--------|--------|
| Eval cases | 50–80 | **67** |
| hit@1 | ≥ 85% | **≥ 96%** (post-tuning) |
| hit@3 | ≥ 95% | **100%** (post-tuning) |
| Existing site-bot tests | pass | **138 passed** |

## Retrieval changes (`company_chatbot/retrieval.py`)

1. **Stopword removal** — low-value tokens stripped before scoring (`STOPWORDS` set).
2. **Typo normalization** — `normalize_query_text()` fixes assisant→assistant, producsts→products, automations→automation, ai-assistant→ai assistant; shared with `modes.py`.
3. **Phrase / alias boost** — global phrase→chunk map plus per-chunk `aliases`; strong boost on near-exact matches.
4. **Topic inference + boost** — lightweight router topics (pricing, product_email, product_crm, workflow_audit, integrations, services, industries, boundaries, company, contact); matching chunks boosted, high-confidence mismatches penalized (soft, not hard filter).
5. **Keyword weighting** — IDF-weighted overlap; keyword/alias field hits weighted higher than body text.
6. **Negative keywords** — per-chunk penalties when query contains off-topic terms (e.g. pricing terms on product_email chunk).
7. **Session-aware query** — `effective_query_for_retrieval()` merges short follow-ups with `previous_user_message`; orchestrator passes prior turn into answer-mode retrieval only.

## KB metadata (`data/company_chatbot/fikiri_kb_chunks.jsonl`)

Optional fields on **28 key chunks**:

- `intent` — finer routing label (e.g. `product_email_assistant`, `pricing_starter`)
- `aliases` — phrase boosts (e.g. `"ai email assistant"`, `"help me"`)
- `negative_keywords` — downrank when query contains these (e.g. product chunk + `"starter"`)

Existing fields unchanged: `id`, `topic`, `source_url`, `keywords`, `text`. `schema_version` remains **v1**.

## Eval harness

- `tests/company_chatbot_retrieval_eval.yaml` — 67 golden queries
- `tests/test_company_chatbot_retrieval_eval.py` — asserts hit@1 ≥ 0.85, hit@3 ≥ 0.95

## Orchestrator touch

`_handle_answer` builds effective query from `previous_user_message` and passes pre-retrieved result to `apply_grounding`. No other mode or session-store changes.

## Before / after (top-1 chunk)

| Query | Before (approx.) | After |
|-------|------------------|-------|
| `I need to find out about the email assisant` | weak / generic overlap | `product_ai_email_assistant` |
| `How much is Starter?` | `faq_plan_fit` or mixed | `pricing_starter` |
| `What about Gmail?` (after email assistant question) | `integration_gmail` without context | `product_ai_email_assistant` or `integration_gmail` with context merge |

## Run tests

```bash
FIKIRI_SITE_BOT_TEST_MODE=1 python3 -m pytest \
  tests/test_company_chatbot_modes.py \
  tests/test_company_chatbot_grounding.py \
  tests/test_company_chatbot_intake.py \
  tests/test_company_chatbot_guards.py \
  tests/test_company_chatbot_scenarios.py \
  tests/test_company_chatbot_lead_scoring.py \
  tests/test_company_chatbot_session_store.py \
  tests/test_company_chatbot_rate_limit.py \
  tests/test_company_chatbot_transcript_store.py \
  tests/test_company_chatbot_retrieval_eval.py \
  tests/test_site_chatbot_api.py \
  tests/test_admin_site_chat_api.py -q
```

## Out of scope (confirmed untouched)

- Frontend (`frontend/**`)
- Tenant chatbot (`core/public_chatbot_api.py`, `core/chatbot_*`)
- Routes (`routes/site_chatbot_api.py`, `app.py`)
- DB / CRM / Slack / email
- LLM / vector / embedding calls

## Ops note

Restart Flask after KB JSONL changes so `_cached_chunks()` reloads in production workers.
