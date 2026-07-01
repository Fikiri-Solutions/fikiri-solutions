# Fikiri Site Bot — Phase 6c Handoff (Pain-Language Navigation)

## Goal

Navigate messy client language by **meaning and service families**, not exact product names. Separate **intent** (mode) from **topic** (service family) and compose **bridge answers** when multiple areas fit.

No LLM, vectors, frontend, or tenant chatbot changes.

## Architecture layers

```
User message
  → mode detection (intent: answer / explore_fit / workflow_audit / …)
  → retrieval (topic: service families + pain phrases + KB chunks)
  → grounding (single evidence | bridge | disambiguation | no evidence)
```

## Service families (`company_chatbot/service_families.py`)

| Family | Client pain examples |
|--------|----------------------|
| `inbox_email` | drowning in emails, automate inbox, Gmail stuff |
| `lead_followup` | slipping through cracks, stop missing leads, website form |
| `crm_tracking` | managing customers, track customers, like a CRM |
| `workflow_audit` | not sure where leak is, map workflow |
| `websites_intake` | website form, intake path |
| `consulting` | small business, cleaning business, Florida SMB |
| (+ pricing, company, contact, industries, boundaries) | |

Chunks may list multiple `service_families` in JSONL. Pain regex rules boost matching chunks without hard-filtering.

## Retrieval (`company_chatbot/retrieval.py`)

- Client-language phrase boosts (17+ pain phrases)
- `family_match_boost()` from inferred pain families
- `RetrievalResult.service_families` and `ambiguous_families` flag

## Grounding (`company_chatbot/grounding.py`)

| Reason | When |
|--------|------|
| `evidence_match` | Clear single-family winner |
| `bridge_multi_family` | Multiple families compete; response opens with “That sounds closest to…” and uses KB text + hints |
| `disambiguation` | Very vague (“I need help”) with weak retrieval |
| `sensitive_topic_without_evidence` | HIPAA / case study / etc. |

Bridge example shape:

> That sounds closest to Fikiri's inbox and email workflow automation and lead capture and follow-up work. [KB evidence]. If messages are piling up in Gmail… If follow-ups are getting missed…

## KB updates

- `service_families` on key product/service chunks
- Client-language `aliases` on email assistant, CRM, Gmail, lead-follow-up chunks

## Eval (`tests/company_chatbot_retrieval_eval.yaml`)

- **84 cases** (67 clean + **17 messy**)
- Targets: hit@1 ≥ 85%, hit@3 ≥ 95%, family match ≥ 90% on messy cases
- Messy cases include `expected_families` in addition to `expected_ids`

## Mode detection note

Pain phrases added to `MODE_ANSWER` use **question/help framing** so intake answers like “Missed leads and manual follow-up” do not interrupt workflow-audit intake.

## Transcript learning loop (operational)

1. Review transcript miss
2. Add one alias, pain rule, or eval case
3. Re-run `tests/test_company_chatbot_retrieval_eval.py`
4. Restart Flask to reload KB cache

## Tests

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

## Files touched

- `company_chatbot/service_families.py` (new)
- `company_chatbot/retrieval.py`
- `company_chatbot/grounding.py`
- `company_chatbot/modes.py` (conservative pain → answer routing)
- `data/company_chatbot/fikiri_kb_chunks.jsonl`
- `tests/company_chatbot_retrieval_eval.yaml`
- `tests/test_company_chatbot_retrieval_eval.py`
- `tests/test_company_chatbot_grounding.py`
