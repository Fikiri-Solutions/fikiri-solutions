# Fikiri Financial Model & Rate Limiting

Summary of **pricing vs. cost**, **cost to acquire and serve a customer**, and **rate limiting** based on the current codebase and advertised plans.

---

## Cost of Operation & Pricing Baseline (Your Overhead)

Use this section to see **all** costs you pay so you can price services and product with a target margin in mind.

### Fixed monthly overhead (you pay regardless of customer count)

| Category | What it is | Typical range (fill in your actuals) |
|----------|------------|--------------------------------------|
| **Hosting – backend** | Render (or similar) for Flask API | $7–25/mo (starter) → $25–85+ (standard/pro) |
| **Hosting – frontend** | Vercel (or similar) for React app | $0 (free) → $20/mo (Pro) |
| **Database** | SQLite on same server today; later PostgreSQL (managed) | $0 today → $15–50/mo (e.g. Neon, Render PG) |
| **Redis** | Sessions, rate limits, cache (Upstash, Render Redis, etc.) | $0 (free tier) → $10–30/mo |
| **Domain(s)** | fikiri.com, etc. | ~$1–2/mo amortized |
| **Email sending** | Transactional (e.g. SendGrid, Resend) if you send auth/notifications | $0 (free tier) → $15–50/mo |
| **Monitoring / logging** | Sentry, LogTail, Datadog, etc. | $0 (free tier) → $25–100/mo |
| **Other SaaS** | Billing, support, compliance, dev tools | $0–100/mo |
| **Total fixed (estimate)** | | **~$25–150/mo** early; **~$100–350/mo** as you scale |

### Variable costs (scale with usage and customer count)

| Driver | Where it appears | Approx. cost |
|--------|------------------|--------------|
| **OpenAI** (LLM + embeddings) | Chat, email classification, RAG, analysis | ~$0.001–0.002 per AI response; embeddings ~$0.0001/1K tokens (§2.1) |
| **Stripe** | Per successful charge | 2.9% + $0.30 per charge (§2.5) |
| **Twilio (SMS)** | Workflow SMS, reminders, opt-in | ~**$0.008–0.01**/segment US outbound (see §2.2); higher for int’l / multi-segment / MMS |
| **Pinecone** | Vector search (RAG) | Per index + queries; low $/tenant unless heavy RAG (§2.3) |
| **Overage** (your product) | Email/lead/AI over plan limits | You charge $0.02 / $0.10 / $0.05; your cost is mainly OpenAI for extra AI, rest is margin |

**Per-customer variable (within plan limits):** see §3 table — roughly **$1.60–1.85** (Starter), **$3.40–4.20** (Growth), **$10–14** (Business) per paying customer/month. Enterprise is unbounded without a cap/alert.

### Foreseeable expenses as you grow

| When | What | Rough cost impact |
|------|------|-------------------|
| **More concurrent users** | More workers / bigger instance or PostgreSQL | +$25–100/mo |
| **PostgreSQL** | Managed DB for write scaling | +$15–50/mo (then scale with plan) |
| **Redis in prod** | Required for production (no in-memory fallback) | +$10–30/mo |
| **Support / compliance** | Help desk, terms, privacy, SOC2 if needed | Tooling $20–100/mo; audit one-time |
| **Enterprise deals** | Custom AI caps, SLAs, maybe dedicated infra | Negotiate; track cost per tenant |
| **Backups / DR** | Automated DB backups, optional multi-region | $5–50/mo |

### Simple pricing check

- **Total monthly cost** ≈ **Fixed overhead** + **Σ (variable per customer × number of customers per tier)**.
- **Minimum price** to stay profitable: ensure **(Revenue − Stripe fees − variable cost per customer)** covers **Fixed overhead ÷ number of paying customers** plus your target margin.
- **Example (10 paying customers, all Starter):** Fixed ~$100, variable ~$18, revenue 10×$49 = $490 → Stripe ~$47, variable ~$18, leaves ~$425; fixed $100 → **~$325 contribution** before your time. **$49 Starter** is fine at low volume; watch **fixed** as you add tools and **variable** on Enterprise/unlimited AI.

**Recommendation:** Once a month, list fixed (actual invoices) and variable (OpenAI, Stripe, Twilio, Pinecone dashboards); compare to revenue by tier. Use that to adjust pricing or caps (e.g. Enterprise AI ceiling) and to set overage fees above your cost.

### Revenue projection: 10–15 clients (with what you have now)

**Sellable today:** Subscriptions (Starter → Enterprise) with 7-day trial; Stripe billing; AI email assistant, CRM, automation, dashboard, Gmail/Outlook integration; tier limits and overage fees. Revenue below is **subscription only**; overage (email/lead/AI) adds on top.

| Scenario | Mix (example) | Monthly revenue | Annual run rate |
|----------|----------------|------------------|------------------|
| **Conservative** | 10–15 all Starter ($49) | $490 – $735 | ~$5.9k – $8.8k |
| **Mid** | e.g. 8 Starter + 4 Growth + 2 Business | $49×8 + $99×4 + $199×2 = $392 + $396 + $398 = **$1,186** | ~$14.2k |
| **Optimistic** | e.g. 6 Starter + 4 Growth + 3 Business + 2 Enterprise | $294 + $396 + $597 + $998 = **$2,285** | ~$27.4k |

**Ranges for 10 vs 15 clients:**

| Clients | If mostly Starter | If mixed (mid) | If 2–3 higher tiers |
|---------|-------------------|----------------|----------------------|
| **10** | $490/mo (~$5.9k/yr) | ~$600–1,200/mo | ~$1,000–1,800/mo |
| **15** | $735/mo (~$8.8k/yr) | ~$900–1,800/mo | ~$1,500–2,800/mo |

**Takeaway:** With 10–15 clients, **$490–$735/mo** is realistic if most are Starter; **$1,000–$2,800/mo** if you land a few Growth/Business (or one Enterprise). After variable cost (~$2–4 per Starter, ~$10–14 per Business), margin stays high; fixed overhead (e.g. $100–150/mo) is covered quickly. Use this as the baseline; add overage and annual-plan revenue when you have data.

---

## 1. What You Charge (Prices)

| Tier        | Monthly | Annual (10% off) | Emails/mo | Leads | AI responses/mo | Users |
|------------|---------|------------------|-----------|-------|------------------|-------|
| **Starter**   | $49   | $529             | 500       | 100   | 200              | 1     |
| **Growth**    | $99   | $1,069           | 2,000     | 1,000 | 800              | 3     |
| **Business**  | $199  | $2,149           | 10,000    | 5,000 | 4,000            | ∞     |
| **Enterprise**| $499  | $5,389           | ∞         | ∞     | ∞                | ∞     |

**Overage** (billing_manager): Email **$0.02** each · Lead **$0.10** each · AI response **$0.05** each.

**Other:** 7-day free trial; Stripe is the billing backend.

**Note:** Keep in-product copy aligned with **$49** Starter, **$99** Growth, **$499** Enterprise.

---

## 2. What You Pay (Cost Drivers)

### 2.1 OpenAI (LLM + embeddings)

**Chat** (`core/ai/llm_client.py`, `core/ai/llm_router.py`):

- Classification/extraction: `gpt-3.5-turbo`, 100–200 tokens → ~$0.0002–0.0005 per call.
- Email reply: ~300 tokens → ~$0.0009 per call.
- General/summarization: ~500 tokens → ~$0.001–0.002 per call.

**Blended cost per "AI response":** ~$0.001–0.002 (~$0.0015 mid-range).

| Tier       | AI responses/mo | Est. OpenAI chat cost/mo |
|------------|------------------|---------------------------|
| Starter    | 200              | ~$0.20–0.40              |
| Growth     | 800              | ~$0.80–1.60              |
| Business   | 4,000            | ~$4–8                    |
| Enterprise | Unlimited        | Unbounded (needs guardrails) |

**Embeddings** (`core/ai/embedding_client.py`): `text-embedding-ada-002` — ~$0.0001 / 1K input tokens. RAG/FAQ cost scales with docs and queries; usually small per tenant.

**LLM is the main variable cost;** embeddings and Pinecone are secondary unless RAG is heavy.

### 2.2 Twilio (SMS)

**What you pay:** Twilio charges **per message segment** (not always “one text = one billable unit”). US long-code / toll-free **outbound** is often roughly **$0.0075–0.009** per segment for standard SMS; **an observed delivered US SMS in production was ~$0.0083** (single segment, GSM encoding). International, **carrier surcharges**, **MMS**, and **long bodies** (multiple segments) cost more — use [Twilio’s pricing page](https://www.twilio.com/en-us/pricing) and your **monthly invoice** as source of truth; refresh this doc when rates change.

**Where it shows up in the product:** Scheduled follow-ups (`core/workflow_followups.py`), automation `send_sms`, and any future SMS surfaces — only when Twilio env vars are set and consent rules pass.

**Financial planning (quick math):**

| Assumption | Formula | Example @ ~$0.0083/segment |
|------------|---------|----------------------------|
| Light SMS tenant | `msgs/mo × $/segment` | 20 → **~$0.17/mo** |
| Medium | same | 100 → **~$0.83/mo** |
| Heavy | same | 500 → **~$4.15/mo** |

**Internal accounting (recommended):**

1. **COGS line:** Treat Twilio SMS as **variable COGS** (same bucket as OpenAI usage), not fixed overhead.
2. **Reconciliation:** Monthly, compare **Twilio Console / invoice** total Messaging spend to **`COUNT(*)` from `sms_messages`** where `status = 'sent'` (and optionally multiply by your **blended realized $/message** from the invoice). Investigate drift (failed messages, refunds, non-app test sends).
3. **Unit economics:** For margin by tier, add **`estimated_sms_cost = sent_messages × blended_rate`** per tenant (or globally × allocation rule) alongside AI spend.
4. **Scorecard (§8):** Extend “COGS % of revenue” notes with **SMS spend vs revenue** when SMS is a marketed feature.

Only when SMS is enabled and customers actually receive messages does this cost bite; consent gating reduces accidental send volume.

### 2.3 Pinecone

Vector search when `PINECONE_API_KEY` is set (`core/minimal_vector_search.py`). Serverless pricing per index, 1M vectors, and queries. Assume low $/tenant unless very large indexes or high query volume.

### 2.4 Render / Vercel

**Render:** backend (Flask) — fixed plan + possible overages. **Vercel:** frontend — free or Pro; no per-customer variable in code.

### 2.5 Stripe

~2.9% + $0.30 per successful charge. On $49: ~$1.72; on $199: ~$6.07; on $499: ~$14.77.

### 2.6 Redis

Rate limiting, cache, sessions. Cost is infra-level (e.g. Upstash/Render Redis), not per-customer.

---

## 3. Cost to Acquire vs. Cost to Serve

**CAC** is not in the repo — it's marketing/sales (ads, content, sales time). Add paid acquisition + content/SEO, divide by new paying customers.

**Cost to serve (variable, per customer/month):**

| Tier       | OpenAI (incl.) | Stripe | Total variable | Gross margin (approx.) |
|------------|----------------|--------|----------------|------------------------|
| Starter    | ~$0.20–0.40    | ~$1.72 | ~$1.92–2.12    | ~$47+                  |
| Growth     | ~$0.80–1.60    | ~$3.17 | ~$4.00–4.80    | ~$94                   |
| Business   | ~$4–8          | ~$6.07 | ~$10–14        | ~$185                  |
| Enterprise | Unbounded       | ~$14.77| —              | Add soft cap or alert  |

**SMS:** Add **`messages_sent × blended $/segment`** (see §2.2). At **~$0.0083/segment**, ~**20–60 msgs/mo/tenant** → **~$0.17–0.50/mo**; 100 msgs → **~$0.83/mo**. Use invoice-derived blended rate for board-level numbers.

**Summary:** Cost to serve is low vs. revenue. Levers: (1) keep LLM on cheaper models where possible, (2) enforce or monitor AI caps on Enterprise, (3) watch Pinecone/embedding use if RAG scales.

---

## 4. Rate Limiting: Current State

### 4.1 Two systems in parallel

1. **Flask-Limiter** (`app.py`, `core/security.py`)
   - Env-driven: `APP_RATE_LIMIT_PER_HOUR` (default 1000), `APP_RATE_LIMIT_PER_MINUTE` (default 100).
   - Supports `redis://` and `rediss://` for shared limits across workers; in-memory fallback only if Redis unavailable.
   - Health endpoints exempt.

2. **EnhancedRateLimiter** (`core/rate_limiter.py`)
   - Redis: sliding window (ZADD + ZCARD + EXPIRE).
   - DB fallback: `rate_limit_requests` table when Redis unavailable; violations in `rate_limit_violations`.

### 4.2 Where limits are applied

- **Auth** (`routes/auth.py`): login 20/15 min per IP, signup 3/hour per IP, forgot/reset password limits. Good for brute-force and signup abuse.
- **General API:** Flask-Limiter default (1000/hr, 100/min per IP). No per-user or per-tier limit on main API.
- **Public chatbot** (`core/public_chatbot_api.py`): API-key limits; minute and hour windows; tied to subscription tier caps.
- **Automation** (`core/automation_safety.py`): per-user and per-contact limits (auto-replies per contact per day, burst, hourly cap). Business-level throttling, not HTTP rate limit.

### 4.3 security.py decorators

`rate_limit_by_user(limit)` and `rate_limit_by_ip(limit)` use Redis; they no-op safely if Redis is unavailable. Recommendation: consolidate around one limiter abstraction.

### 4.4 Efficiency and recommendations

**Efficient:** Redis sliding window is O(1) per request; auth is explicitly limited; DB fallback now enforces limits.

**Risks / improvements:**

- General API is mostly IP-based — good for abuse; less ideal for fair-use behind shared NAT.
- Tier-based limits are strongest on API-key/public flows; main authenticated API is not fully tier-enforced.
- Multiple mechanisms (Flask-Limiter, EnhancedRateLimiter, API-key, AutomationSafety) — consider one Redis backend and one place that knows "user X, tier Y → N req/hour"; keep policy definitions centralized.
- Fail-open is a business choice — consider fail-closed on auth and expensive AI endpoints if abuse appears.

**Summary:** Redis and DB fallback are functional and efficient. Auth and public chatbot are well covered; core app API needs fuller tier-aware enforcement. Long-term: simplify limiter architecture.

---

## 5. Capacity: How Many Clients Can We Handle?

With current setup (Render, gthread Gunicorn, SQLite, optional Redis): **low hundreds of concurrent active users** and **thousands of total registered/paying clients** (e.g. 5k–20k accounts). Main limit: **SQLite write throughput/contention**.

### 5.1 Stack today

| Layer      | Config | Limit / behavior |
|------------|--------|------------------|
| Backend    | Gunicorn gthread, workers × threads (e.g. 4×4) | Throughput depends on CPU and blocking I/O. |
| Database   | SQLite `data/fikiri.db` (WAL) | Reads scale; writes serialized. `DatabaseOptimizer` uses SQLite unless constructed with `db_type="postgresql"`. |
| Rate limit | Env defaults + auth/API-key limits | Per-IP for Flask-Limiter; specialized limits for auth and chatbot. |
| Redis      | `REDIS_URL` | Shared state across workers when available; in-memory fallback otherwise. |
| Disk       | Render 1 GB volume | Enough for SQLite + logs for tens of thousands of users. |

### 5.2 Concurrent vs total clients

- **Concurrent:** ~100–400 active users is a reasonable envelope before noticeable latency/queueing under burst (CPU, blocking I/O, SQLite writes).
- **Total:** SQLite can store hundreds of thousands to millions of rows with indexes. 1 GB disk is enough for tens of thousands of users. **Rough range: 5k–20k+** accounts from a data perspective if peak concurrent load stays in the low-hundreds.

### 5.3 External services

OpenAI, Twilio, Stripe, Pinecone: limits are per your account or per tenant; you hit **cost** or **provider rate limits** before client count alone breaks the app.

### 5.4 How to scale

| Metric                 | Current (theory) | Bottleneck                    |
|------------------------|------------------|-------------------------------|
| Concurrent active users | ~100–400       | SQLite write contention, CPU |
| Total registered clients | ~5k–20k+      | SQLite at peak; disk fine    |

**Next steps:** (1) More workers if needed; (2) **PostgreSQL** + `DATABASE_URL` and wire app to it for concurrent writes; (3) Redis for sessions and rate limiting; (4) Async workers (gevent/eventlet or ASGI) for I/O-bound load. The main scaling unlock is moving write-heavy production off SQLite to PostgreSQL.

---

## 6. Action Items

**Financial / product**

- Align FAQ and copy with **$49** Starter, **$99** Growth, **$499** Enterprise.
- Add **Enterprise guardrails:** per-tenant AI cap or spend alert.
- Track **cost per tenant** in analytics: OpenAI + **SMS (Twilio invoice or `sms_messages` × blended rate)** + allocatable infra.

**Rate limiting**

- Keep Redis in all production/staging (avoid memory fallback in prod).
- Expand tier-aware limits from API-key/public to core authenticated endpoints.
- Consolidate policy definitions to reduce drift between Flask-Limiter, enhanced limiter, and automation safety.

**Cost-efficiency**

- Current architecture is acceptable for early-stage (low hundreds concurrent) if Redis is configured.
- **Highest ROI:** Move to PostgreSQL before sustained write-heavy growth.
- Add monthly AI budget alarms per tenant; soft-stop/approval near cap for Enterprise.
- One backend instance class until p95 latency or queue depth shows saturation.
- Instrument: p95 latency, request rate, DB lock/wait errors, Redis availability, OpenAI spend per tenant.

---

## 7. Recommendation: Is the Model Good Enough Now?

**Yes, for now,** with guardrails. Pricing-to-variable-cost spread is strong; rate-limit and runtime fixes improved reliability.

**Do soon:** (1) AI spend guardrails per tenant, (2) Plan PostgreSQL migration before sustained write-heavy growth.

Once you have **CAC** and **LTV** (retention × ARPU), add a short "CAC vs LTV" section and tie it to the cost-to-serve numbers above.

---

## 8. Immediate Focus (Next 30 Days)

### Week 1: Revenue protection

1. Enforce plan entitlements on all expensive authenticated endpoints (tier-aware ceilings, AI usage checks).
2. Set AI spend guardrail defaults: Starter/Growth/Business — alert + hard stop at cap; Enterprise — alert + approval over cap.
3. Remove stale $29 and outdated tier references from user-facing copy and dashboards.

### Week 2: Monitoring

1. Executive dashboards/alerts: OpenAI spend per tenant/day, gross margin per tenant, rate-limit rejects by endpoint/tier, automation failures and retry exhaustions.
2. SLOs for Automation Studio (e.g. ≥99% successful executions, p95 start delay &lt; 60s); alert on breach.

### Week 3: Reliability under stress

1. Stress tests: Gmail→CRM bursts, webhook fanout, AI scoring bursts.
2. Backpressure: queue and retry with jitter/backoff; dead-letter failed jobs with operator visibility.
3. Runbooks: Redis down, OpenAI 429/5xx, Gmail quota, webhook destination failures.

### Week 4: Scale risk reduction

1. PostgreSQL migration plan (dual-write or phased); rollback and rehearsal.
2. Production hardening: Redis required in prod/staging; fail-closed for high-cost/high-risk endpoints where abuse risk is material.

### Operator scorecard (weekly)

- MRR growth, net revenue retention
- COGS % of revenue (overall and by tier)
- AI spend per active tenant
- Automation success rate, p95 execution latency
- DB lock/wait errors
- Support tickets per 100 active customers

### Defer (stay lean)

- Separate admin portal (use RBAC in current app first).
- Multi-region, premature microservices, custom enterprise-only architecture before enterprise revenue justifies it.
