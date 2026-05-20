# Chatbot production go-live checklist (SMB / early-scale)

**Audience:** First paid SMB deployments, agency embeds, low-to-mid traffic.  
**Not for:** Enterprise compliance (SOC2/HIPAA/GDPR), high-QPS, or “zero hallucination” SLAs.

**Canonical architecture:** [CHATBOT_ARCHITECTURE.md](./CHATBOT_ARCHITECTURE.md)  
**CI / merge checks:** [CHATBOT_PRODUCTION_CHECKLIST.md](./CHATBOT_PRODUCTION_CHECKLIST.md)  
**Embed contract:** [CHATBOT_EMBED.md](./CHATBOT_EMBED.md)

---

## 1. Launch posture

### Ready now

- Modular chatbot stack (retrieval → gates → LLM → lead capture → usage recording)
- Tenant-scoped KB + vector search with chunked ingest and chunk cleanup
- Vector diversity + cross-source dedup (deterministic, no ML reranker)
- Public widget `schema_version: v1` + dashboard preview parity
- Per-tenant chatbot config (whitelist keys only)
- Structured observability events (counts/IDs, no PII in log extras)
- Regression tests for retrieval, preview, public API, lead capture, usage/billing
- Fallback + schema-validated LLM responses

### Safe to promise first paid SMB clients

- Website embed chatbot with API key auth
- FAQ + knowledge-base answers with cited-style `sources`
- Lead capture when email (or configured fields) is provided
- Plan/tier/budget usage limits (402 when exceeded)
- Builder preview and KB import/vectorize/revectorize
- Human escalation path on low confidence (when configured)
- Support via logs using structured `chatbot.*` events

### Do not promise yet

- Long-term conversation memory across sessions/devices (preview supports `conversation_id`; durable store is limited)
- Formal eval harness / hallucination-free answers
- Real-time analytics dashboard or source-quality SLAs
- Phone-only lead capture without email
- Enterprise security attestations
- Automatic retraining or semantic caching
- High-volume async vector pipelines with guaranteed SLA

---

## 2. Required environment and config

Verify in **Render (backend)** and **Vercel (frontend)** (or your host equivalents).

### Public widget and API

| Check | Variable / setting | Notes |
|-------|-------------------|--------|
| [ ] | **Public API base URL** | e.g. `https://<backend-host>/api` — must match embed `apiUrl` / Vite proxy in dev |
| [ ] | **Frontend origin** | Customer site origin allowed if using CORS-restricted keys (`allowed_origins` on key) |
| [ ] | **API key** | Create via dashboard `POST /api/user/api-keys` (scope must include `chatbot:query`) — store `fik_...` secret; never commit |
| [ ] | **Key status** | `GET /api/public/chatbot/key-status` with `X-API-Key` returns `valid: true` before go-live |

### LLM

| Check | Variable | Default / notes |
|-------|----------|-----------------|
| [ ] | `OPENAI_API_KEY` | Required for LLM answers (`core/ai/llm_router.py`) |
| [ ] | `OPENAI_TIMEOUT` | Optional; default 30s |
| [ ] | Model routing | Via `LLMRouter` / intent `chatbot_response` — confirm prod model policy in `core/ai/` config |
| [ ] | `CHATBOT_CONFIDENCE_THRESHOLD` | Default `0.4` — below → clarifying/fallback message |

### Vector backend

| Check | Variable | Notes |
|-------|----------|--------|
| [ ] | Feature flag `vector_search` | Must be enabled in `data/feature_flags.json` (or env override) for vector retrieval |
| [ ] | `PINECONE_API_KEY` | If using Pinecone (production recommended at scale) |
| [ ] | `PINECONE_INDEX_NAME` | Default `fikiri-vectors` |
| [ ] | `PINECONE_EMBEDDING_MODEL` | If set, Pinecone path used for embeddings |
| [ ] | Local fallback | Without Pinecone: `data/vector_db.pkl` on disk — OK for dev/small tenants; confirm persistence on Render disk/volume |

### Retrieval tuning (optional overrides)

| Variable | Default | Effect |
|----------|---------|--------|
| [ ] `FIKIRI_CHATBOT_CONTEXT_MAX_CHARS` | `6000` | Max prompt context length |
| [ ] `FIKIRI_CHATBOT_VECTOR_FETCH_TOP_K` | `12` | Raw vector candidates before diversity |
| [ ] `FIKIRI_CHATBOT_MAX_CHUNKS_PER_PARENT` | `2` | Max chunks per document in context |
| [ ] `FIKIRI_CHATBOT_ADJACENT_CHUNK_SCORE_GAP` | `0.08` | Allow adjacent chunk if score within gap |
| [ ] `FIKIRI_CHATBOT_STRONG_VECTOR_SCORE_GAP` | `0.15` | Prefer vector over KB when score gap large |

### Database, billing, rate limits

| Check | Item | Notes |
|-------|------|--------|
| [ ] | `DATABASE_URL` | **Postgres** in production (`FLASK_ENV=production` rejects SQLite) |
| [ ] | `subscriptions` / plan | Paid status → `allow_llm` for widget LLM path |
| [ ] | Tier caps | `ai_responses` tier usage via `check_tier_usage_cap` |
| [ ] | AI budget | `ai_budget_guardrails` soft-stop → 402 `AI_BUDGET_SOFT_STOP` |
| [ ] | API key rate limits | Per-key minute/hour limits on `@require_api_key` routes |
| [ ] | `billing_usage` table | Exists in prod DB for `chatbot_queries` metering |

### Logging

| Check | Variable | Notes |
|-------|----------|--------|
| [ ] | `LOG_LEVEL` | Recommend `INFO` in prod; `DEBUG` only for short investigations |
| [ ] | `FLASK_ENV` | `production` on Render prod service |
| [ ] | Log aggregation | Filter on `event` field (see §4) — **never** expect raw query/email in structured extras |

**Note:** `FIKIRI_EMAIL_PIPELINE_AI_GATE` applies to the **email mailbox** pipeline, not the public chatbot widget.

---

## 3. Pre-launch verification

Complete in order for each new paying tenant (or template tenant).

| Step | Action | Pass criteria |
|------|--------|---------------|
| [ ] | **Create API key** | `chatbot:query` scope; copy key once; record tenant `user_id` / `tenant_id` |
| [ ] | **Embed on test page** | SDK or fetch to `POST /api/public/chatbot/query` — widget loads, no console CORS errors |
| [ ] | **Upload/import KB** | `POST /api/chatbot/knowledge/import` (session or API key per your flow) |
| [ ] | **Add FAQs** (optional) | Builder or `POST /api/chatbot/faq` |
| [ ] | **Vectorize / revectorize** | Large docs chunked; metadata has `parent_doc_id`, `chunk_count`; revectorize does not orphan old chunks |
| [ ] | **Save chatbot config** | `PUT /api/chatbot/config` — tone, fallback, `lead_capture_enabled`, etc. |
| [ ] | **Builder preview** | `POST /api/chatbot/preview-query` — answer matches expected KB |
| [ ] | **Preview + debug** | Body `{ "query": "...", "debug": true }` → `retrieval_debug` with sensible counts |
| [ ] | **Public widget query** | Same question via public endpoint → `schema_version: v1`, `response`, `sources` |
| [ ] | **No public debug** | Public JSON must **not** contain `retrieval_debug` |
| [ ] | **Lead capture** | Query with email or `lead` object → `lead_id` when enabled; CRM lead exists |
| [ ] | **Lead disabled** | `lead_capture_enabled: false` → no CRM write; `chatbot.lead_capture.skipped` with `disabled_by_config` |
| [ ] | **Usage events** | Logs show `chatbot.usage.request_recorded`; paid plan shows `billing_recorded` / `ai_recorded` when LLM validates |
| [ ] | **Fallback** | Empty KB + off-topic query → `fallback_used: true`, safe message, no 500 |
| [ ] | **Blocked plan** (staging) | Free/unpaid key or tier cap → 402 with clear `error_code` |

**Quick curl (public smoke):**

```bash
curl -sS -X POST "$API_URL/api/public/chatbot/query" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $FIKIRI_API_KEY" \
  -d '{"query":"What are your hours?"}' | jq '.schema_version, .retrieval_debug, .lead_id, .fallback_used'
# Expect: "v1", null, <optional>, false/true
```

---

## 4. Monitoring checklist

Search logs by `event` (structured `extra`). Counts are safe; **do not** index log bodies for customer email/query text.

| Event | Meaning | When it appears | What to check |
|-------|---------|-----------------|---------------|
| `chatbot.retrieval.completed` | FAQ/KB/vector pipeline finished | Every widget/preview query | `raw_*_count`, `post_vector_diversity_count`, `final_source_count`, `collapsed_duplicate_count`, `fallback_needed`, `latency_ms` |
| `chatbot.usage.request_recorded` | API key usage row written | Each public request (incl. 402) | `api_key_id`, `response_status` — spike = traffic or abuse |
| `chatbot.usage.billing_recorded` | `billing_usage` chatbot_queries +1 | Successful 200 public queries | Missing on 200 → billing insert failure |
| `chatbot.usage.ai_recorded` | AI budget counter incremented | LLM attempted + validated JSON only | High volume vs tier; should not fire on fallback-only |
| `chatbot.usage.blocked` | Request stopped before LLM | 402 plan/tier/budget | `blocked_reason`: `plan_not_allowed`, `tier_cap_exceeded`, `ai_budget_soft_stop` |
| `chatbot.lead_capture.completed` | Lead found or created + activity | Widget with contact info | `lead_id`, `created` true/false |
| `chatbot.lead_capture.skipped` | No CRM write | Disabled config or no contact | `reason`: `disabled_by_config`, `no_contact_info`, `collect_email_disabled`, etc. |
| `chatbot.lead_capture.failed` | CRM/DB error during capture | Exception in lead path | `error_type` — response may still be 200; fix CRM/DB |
| `chatbot_config_load_warning` | Config load fell back to defaults | DB/metadata issue | Tenant using defaults — fix config row |

**Healthy signals:** retrieval `final_source_count` > 0 for on-topic questions; low `fallback_needed` rate after KB fill; few `lead_capture.failed`.

**Alert candidates (manual or future automation):** spike in `usage.blocked`, `lead_capture.failed`, or `fallback_needed` > 30% over 1h.

---

## 5. Runbook (quick actions)

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| **Bad / wrong answer** | Stale vectors, weak KB, or LLM drift | Revectorize doc; add FAQ; preview with `debug: true`; check `sources` types/ids; tune config tone; do **not** promise zero errors |
| **Fallback too often** | Empty KB, low retrieval confidence, or threshold | Import content; lower `CHATBOT_CONFIDENCE_THRESHOLD` only with care; check `retrieval_debug.raw_vector_count` |
| **Widget fails to load** | Wrong `apiUrl`, CORS, or JS error | Verify `key-status`; browser network tab; `allowed_origins` on key |
| **API key rejected** | Revoked key, wrong scope, invalid header | Regenerate key with `chatbot:query`; use `X-API-Key` or `Authorization: Bearer` |
| **Usage blocked (402)** | Plan, tier cap, or AI budget | Read `error_code` + `chatbot.usage.blocked`; upgrade plan or approve budget |
| **Lead capture fails** | CRM/DB error | Log `chatbot.lead_capture.failed`; verify `leads` table and `enhanced_crm_service`; email still required for create |
| **Weak vector sources** | Flag off, Pinecone down, or no ingest | Enable `vector_search`; check Pinecone env; revectorize; inspect `post_vector_diversity_count` |
| **Updated docs, old answers** | Cache not the issue — vectors stale | **Revectorize** after edit (`sync_kb_document_vectors` / builder revectorize); confirm `chunk_count` updated |
| **High latency** | LLM or vector slow | Check `retrieval_debug.latency_ms` vs total; reduce `CONTEXT_MAX_CHARS`; verify Pinecone region |

---

## 6. Release checklist (every deploy)

Before merging to `main` or after Render/Vercel deploy:

- [ ] `pytest tests/test_chatbot_*.py tests/test_public_chatbot_api.py tests/test_revenue_chatbot_flow.py tests/test_chatbot_lead_capture.py tests/test_chatbot_usage_tracking.py -v`
- [ ] `cd frontend && npx vitest run src/__tests__/ChatbotBuilder.test.tsx src/__tests__/chatbotBuilderPreview.test.ts src/__tests__/apiClientChatbotPreview.test.ts src/__tests__/ChatbotRetrievalDebugPanel.test.tsx`
- [ ] Skim [CHATBOT_ARCHITECTURE.md](./CHATBOT_ARCHITECTURE.md) — module table still matches imports in `public_chatbot_api.py` / `chatbot_smart_faq_api.py`
- [ ] **Spot-check public widget** — one `POST /api/public/chatbot/query` on staging/prod (v1, no `retrieval_debug`)
- [ ] **Spot-check preview** — one authenticated `preview-query` with `debug: true` on staging

---

## 7. Deferred (enterprise / scale)

Not required for first SMB go-live; track as roadmap:

- Durable conversation persistence (cross-device history, replay, eval joins)
- Formal eval harness (golden sets, regression on answer quality)
- High-volume **async** vector jobs (queues, DLQ, idempotent workers)
- Enterprise compliance documentation (SOC2, HIPAA, GDPR DPA)
- Advanced abuse detection (bot traffic, prompt-injection firewall)
- Analytics dashboard (fallback rate, source hits, lead conversion)
- Semantic caching and optional reranking
- Phone-only lead dedupe and advanced lead scoring

---

## 8. Guardrails (sales, support, engineering)

- **Do not claim** “zero hallucinations” or guaranteed factual accuracy — cite KB/FAQ sources and offer escalation.
- **Do not expose** `retrieval_debug` on `POST /api/public/chatbot/query` — dashboard preview + `debug: true` only.
- **Do not log** raw queries, responses, emails, phones, or API key strings in structured fields.
- **Do not add** chatbot business logic to `public_chatbot_api.py` or `chatbot_smart_faq_api.py` except HTTP/auth orchestration — use modules in [CHATBOT_ARCHITECTURE.md](./CHATBOT_ARCHITECTURE.md).
- **Do not bypass** chatbot config whitelist — never merge raw `users.metadata` into prompts.
- **Do not disable** tenant filters on KB search or vector `tenant_id` for “debugging” in production.

---

## Sign-off (per tenant go-live)

| Role | Name | Date | Notes |
|------|------|------|-------|
| Engineering | | | Pre-launch §3 complete |
| Support | | | Runbook §5 acknowledged |
| Customer success | | | §1 “safe to promise” aligned with contract |
