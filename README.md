# Fikiri Solutions - AI-Powered Business Automation

We help small and large businesses save money through automation. Gmail and Outlook lead management, AI-powered responses, CRM integration, and workflow automation, all in one platform.

## 🚀 Quick Start

1. **Copy environment and install backend:**
   ```bash
   cp env.template .env
   # Edit .env with your keys (see Configuration below)
   pip install -r requirements.txt
   ```

2. **Start the backend:**
   ```bash
   python app.py
   ```
   Backend runs at `http://localhost:8081` by default (set `PORT` or `FLASK_RUN_PORT` to override). Database initializes on first run.

3. **Start the frontend (separate terminal):**
   ```bash
   cd frontend && npm install && npm run dev
   ```
   Frontend runs at `http://localhost:5173` (Vite). Use the web UI to sign up, connect Gmail/Outlook, and use the dashboard.

4. **Optional – Google OAuth for Gmail:**  
   Follow [Google OAuth Setup](docs/GOOGLE_OAUTH_SETUP.md) and set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` in `.env`.

## 🔧 Configuration

### Environment Variables

Copy `env.template` to `.env`. Key variables:

- **Auth / API:** `JWT_SECRET_KEY`, `OPENAI_API_KEY`
- **Gmail:** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`
- **Outlook:** `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `MICROSOFT_TENANT_ID`, `MICROSOFT_REDIRECT_URI`
- **Database:** `SQLITE_DATABASE_URL` (dev) or `DATABASE_URL` (production)
- **Redis:** `REDIS_URL` (caching, rate limits, queues)
- **Stripe (billing):** `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`

See `env.template` for the full list and section comments.

### Google OAuth (Gmail)

Required scopes: Gmail read/send/modify, userinfo email/profile. See [Google OAuth Setup](docs/GOOGLE_OAUTH_SETUP.md).

## 📁 Project Structure

```
Fikiri/
├── app.py                    # Flask app entry (backend)
├── routes/                   # API routes (auth, business, user)
├── core/                     # Shared backend (ai, jwt, redis, webhooks, etc.)
├── crm/                      # CRM models and service (crm/service.py canonical)
├── email_automation/         # Email pipeline, jobs, Gmail sync
├── integrations/             # External connectors (Gmail, Outlook, iCloud)
├── analytics/                # Reporting, dashboard API
├── frontend/                 # React + Vite + TypeScript
│   └── src/
│       ├── components/       # UI components (radiant, layout, etc.)
│       ├── pages/            # Page components
│       ├── hooks/            # Custom hooks
│       ├── contexts/         # Auth, theme
│       └── services/         # API client (single backend entry)
├── tests/                    # Backend tests (pytest)
├── scripts/                  # Automation readiness, DB tools
├── docs/                     # Documentation
├── env.template              # Env template (copy to .env)
└── requirements.txt
```

## 🛠️ Commands

- **Backend:** `python app.py` — starts API (and SocketIO if configured) on port 8081.
- **Frontend:** `cd frontend && npm run dev` — Vite dev server (default 5173).
- **Tests:** `pytest tests/ -v` (backend); `cd frontend && npm run test` (frontend).
- **Optional CLI:** `python main_minimal.py setup` / `status` / `config` for Gmail auth and status.

## ✅ Features

- **Email:** Gmail/Outlook integration, parsing, classification, embedded images, auto-replies.
- **CRM:** Contact and lead management (`crm/service.py`), scoring, pipelines.
- **AI:** LLM via `core/ai/` (router, client, validators), chatbot and public API.
- **Automation:** Workflows, follow-ups, appointment reminders, webhooks.
- **Billing:** Stripe subscriptions and 7-day free trial.
- **Frontend:** Dashboard, inbox, CRM, automations, billing, landing (responsive, dark mode, safe-area).

## 🧪 Testing

- **Backend:** `pytest tests/ -v`
- **Public API:** `python tests/run_public_api_tests.py` (see docs for env)
- **Frontend:** `cd frontend && npm run test`

## 🚀 Deployment

1. Set production env vars (do not commit `.env`); use Render/Vercel env or Doppler/Infisical.
2. Backend: `pip install -r requirements.txt`, then run with gunicorn or similar (see `PORT`).
3. Frontend: `cd frontend && npm run build`; serve `dist/` or deploy to Vercel.
4. Ensure Redis and (for production) PostgreSQL are configured.

## 📝 License

This project is part of Fikiri Solutions - AI-powered business automation.
