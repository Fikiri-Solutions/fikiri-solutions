## Fikiri Capacity & Scaling Summary (For Pitching)

### Current Hosting & Concurrency

- **Platform**: Render, `web` service (`fikiri-backend`) on **Starter** plan.
- **Runtime**: Gunicorn with gthread workers:
  - `WEB_CONCURRENCY=4` workers, `GUNICORN_THREADS=4` threads → **up to 16 concurrent worker threads** per instance.
- **Load balancer**: Render’s **managed HTTP load balancer** fronts the service and distributes traffic to Gunicorn workers.

### Observed Performance (Local k6 Tests)

- **Steady-state automations profile** (`npm run k6:steady`):
  - 3–5 virtual users simulating an open Automations dashboard.
  - **p95 latency ~95–100ms** across health + automations endpoints.
  - All key endpoints (`/api/health`, `/api/automation/rules|logs|suggestions`, `/api/automation/test/preset`) consistently return **200** with low single‑digit millisecond backend times.
  - Elevated k6 failure rate is driven by **intentional 401s on `/api/automation/metrics`** (auth guard), not by performance limits.
- **Stress / hammer profile** (`npm run k6:stress`):
  - Up to 30 VUs hammering automations APIs.
  - Backend remains healthy and responds with **rate‑limited 429s** once per‑IP limits are exceeded (`100 per minute`), demonstrating that **guardrails hold under abuse**.

### Practical Capacity Estimates (Per Backend Instance)

These are conservative, directional numbers based on the above behavior and typical SaaS usage patterns.

- **Clients / Tenants**
  - Comfortable with **50–150 actively using clients** on a single instance (dashboards, automations, chat) at the same time.
  - Total onboarded tenants: **hundreds** before scaling becomes necessary.

- **Email Volume (Classification + Automations)**
  - Budgeting **5–10 email-related operations/second**:
    - **18k–36k emails/hour**, **hundreds of thousands/day** can be read, classified, and routed, assuming:
      - Heavy LLM work is queued.
      - Caching is used for repeated patterns.

- **Chatbots / AI Assistants**
  - Budgeting **2–5 AI chatbot turns/second**:
    - **50–100 concurrent active chat sessions** (each user sending a message every 10–30s).
    - On the order of **5k–10k chatbot messages/day** per backend instance, with room to grow via queues and caching.

- **CRM / Leads**
  - Lead storage: **hundreds of thousands of leads** on a properly indexed relational database without issue; millions once on a tuned Postgres tier.
  - Lead/CRM updates: **10–20 mutations/second** → **36k–72k lead updates/hour**.
  - Easily supports **dozens of clients** each working **hundreds of leads/day**.

- **AI / Smart API Responses**
  - With **1–3 LLM calls/second** reserved for AI features:
    - **3.6k–10.8k AI responses/hour**, up to **~100k–250k/day** if needed.
  - Enough for **tens of customers** using smart replies, FAQs, and analytics, as long as:
    - Expensive flows are queued.
    - Per‑tenant rate limits are enforced (already in place).

### Scaling Path on Render

- **Scale up**: move `fikiri-backend` to a larger Render plan (more CPU/RAM) to increase capacity per instance.
- **Scale out**: add more instances of the `fikiri-backend` web service; Render’s managed load balancer will distribute traffic across instances.
- **Rough rule of thumb**:
  - Each additional instance gives **~1× more throughput** (same configuration).
  - Two to three instances are sufficient for **hundreds of active small/medium customers** before more advanced partitioning or regionalization is needed.

