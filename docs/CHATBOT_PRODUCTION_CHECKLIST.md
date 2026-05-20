# Chatbot production checklist

Use with [CHATBOT_ARCHITECTURE.md](./CHATBOT_ARCHITECTURE.md) before merging to `main` and deploying Render + Vercel.

## Pre-merge verification (local / CI)

```bash
# Backend — chatbot + public API
pytest tests/test_chatbot_*.py tests/test_public_chatbot_api.py \
  tests/test_public_chatbot_tenant_isolation.py tests/test_revenue_chatbot_flow.py \
  tests/test_revenue_billing_security.py tests/test_kb_vector_sync.py -v

# Frontend — builder preview + debug
cd frontend && npx vitest run \
  src/__tests__/ChatbotBuilder.test.tsx \
  src/__tests__/chatbotBuilderPreview.test.ts \
  src/__tests__/apiClientChatbotPreview.test.ts \
  src/__tests__/ChatbotRetrievalDebugPanel.test.tsx
```

Full unit suite (optional): `pytest tests/ -q --ignore=tests/integration`

## Environment (production)

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | LLM answers (via `LLMRouter`) |
| Feature flag `vector_search` | Chunked vector retrieval |
| `FIKIRI_CHATBOT_VECTOR_FETCH_TOP_K` | Default `12` (diversity pool) |
| `FIKIRI_CHATBOT_MAX_CHUNKS_PER_PARENT` | Default `2` |
| `FIKIRI_CHATBOT_CONTEXT_MAX_CHARS` | Default `6000` |
| `CHATBOT_CONFIDENCE_THRESHOLD` | Default `0.4` |
| Postgres `DATABASE_URL` | Production DB (not SQLite) |

Optional gates: `FIKIRI_EMAIL_PIPELINE_AI_GATE` applies to **email** pipeline, not public chatbot widget.

## Post-deploy smoke tests

1. **Public widget** — `POST /api/public/chatbot/query` with valid `X-API-Key`:
   - Response includes `schema_version: "v1"`, `response`, `sources`, `confidence`
   - No `retrieval_debug` in body
2. **Preview** — Authenticated `POST /api/chatbot/preview-query` with `debug: true`:
   - Includes `retrieval_debug` counts only (no raw doc text in debug object)
3. **Lead capture** — Query with email or `lead` payload → `lead_id` when `lead_capture_enabled`
4. **Billing** — Paid plan: `ai_usage_recorded: true` only after validated LLM JSON
5. **Logs** — Search for `chatbot.retrieval.completed`, `chatbot.lead_capture.completed`, `chatbot.usage.request_recorded` (no emails/phones in structured fields)

## Known non-goals (this release)

- Durable cross-session conversation store (preview `conversation_id` only)
- Public exposure of `retrieval_debug`
- Phone-only lead dedupe
- Semantic cache / reranker

## Rollback

- Revert merge commit on `main`; Render auto-deploys previous image.
- Vector chunks: revectorize affected KB docs if ingest metadata regressed.
