# Fikiri Site Bot — Phase 6a Handoff

KB coverage and conversation polish sprint. No orchestrator rewrite, LLM, vectors, frontend, or persistence changes.

## Delivered

| Area | Change |
|------|--------|
| KB | `data/company_chatbot/fikiri_kb_chunks.jsonl` expanded to **43 evidence chunks** |
| Products | Email assistant, CRM, AI copilot, integrations (Gmail/Outlook) |
| Services | Workflow audit, consulting, five-beats framework, Florida SMB |
| Industries | Landscaping, restaurant, dental/medical, home services, professional services |
| Boundaries | Websites, compliance claims, case studies (honest, no fake certifications) |
| Transitions | `conversational.py` — help/confusion replies, email-assistant routing hints |
| Guards | More frustration phrases, clearer handoff copy |
| Scenarios | Email assistant, Gmail, Florida audit, help-me, frustration exit |

## KB sources mined

- `frontend/src/pages/About.tsx`, `FaqPage.tsx`, `PricingPage.tsx`
- `docs/sales/FLORIDA_SMB_WORKFLOW_AUDIT_TALKING_POINTS.md` (factual slices only)

## Test command

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
  tests/test_site_chatbot_api.py \
  tests/test_admin_site_chat_api.py -q
```

## Not in scope

- LLM polish, vectors, orchestrator rewrite, frontend, CRM/Slack/email, tenant chatbot

## Next (6b optional)

- Weekly transcript → scenario loop
- More industry-specific chunks from real intake forms
