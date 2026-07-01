# Fikiri Site Bot Phase 4 Handoff

**Status:** Complete (marketing widget)  
**Prior:** [FIKIRI_SITE_BOT_PHASE_3_HANDOFF.md](./FIKIRI_SITE_BOT_PHASE_3_HANDOFF.md)

## What Phase 4 Added

- `frontend/src/services/siteChatApi.ts` — calls `POST /api/site/chat/session/start` and `/message` (no API key)
- `frontend/src/components/FikiriSiteChatWidget.tsx` — branded floating chat UI
- `frontend/src/components/MarketingChatWidget.tsx` — env gate (`VITE_SITE_CHAT_WIDGET_ENABLED`)
- Marketing pages use `MarketingChatWidget` instead of `PublicChatbotWidget`
- Frontend tests: `siteChatApi.test.ts`, `FikiriSiteChatWidget.test.tsx`, `MarketingChatWidget.test.tsx`

## Unchanged (by design)

- `PublicChatbotWidget.tsx` — tenant embed product (install flow / client sites)
- `core/public_chatbot_api.py`, `core/chatbot_*`, chatbot builder
- `company_chatbot/` orchestrator, intake, guards, KB
- No DB, CRM, Slack/email, LLM polish

## Widget behavior

- Launcher bubble (bottom-right)
- Session start on first open → welcome message
- User messages → grounded answers, intake progress label, handoff link (`/intake` or `/contact`)
- Footer: “Powered by Fikiri Solutions”

## Env

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_SITE_CHAT_WIDGET_ENABLED` | enabled | Set `false` to hide marketing widget |
| `VITE_API_URL` | auto | Must reach backend with `/api/site/chat` routes |

## Tests

**Backend (unchanged):**

```bash
FIKIRI_SITE_BOT_TEST_MODE=1 python3 -m pytest \
  tests/test_company_chatbot_modes.py \
  tests/test_company_chatbot_grounding.py \
  tests/test_company_chatbot_intake.py \
  tests/test_company_chatbot_guards.py \
  tests/test_company_chatbot_scenarios.py \
  tests/test_site_chatbot_api.py -q
```

**Frontend:**

```bash
cd frontend && npx vitest run src/__tests__/siteChatApi.test.ts \
  src/__tests__/FikiriSiteChatWidget.test.tsx \
  src/__tests__/MarketingChatWidget.test.tsx
```

## Marketing pages wired

`/`, `/about`, `/pricing`, `/faq`, `/contact`, `/intake`, industry landings, legal pages, classic landing — all use `MarketingChatWidget`.

## Next Phase (suggested)

- Phase 5: DB session persistence + CRM lead write + notifications (explicit scope only)
