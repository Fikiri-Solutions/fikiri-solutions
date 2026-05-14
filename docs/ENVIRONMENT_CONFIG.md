# 🔧 Environment Configuration

## Sanitized .env Template

```bash
# =============================================================================
# APPLICATION SETTINGS
# =============================================================================
FLASK_ENV=production
FLASK_SECRET_KEY=your-flask-secret-key-32-chars
CORS_ORIGINS=https://fikirisolutions.com,https://www.fikirisolutions.com
PORT=5000

# =============================================================================
# DATABASE CONFIGURATION  
# =============================================================================
DATABASE_URL=your-postgresql-or-sqlite-url
SQLALCHEMY_DATABASE_URI=${DATABASE_URL}
SQLALCHEMY_TRACK_MODIFICATIONS=False

# =============================================================================
# GOOGLE OAUTH CONFIGURATION
# =============================================================================
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://fikirisolutions.com/api/oauth/gmail/callback

# Legacy Gmail API (for compatibility)
GMAIL_CLIENT_ID=${GOOGLE_CLIENT_ID}
GMAIL_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
GMAIL_REDIRECT_URI=${GOOGLE_REDIRECT_URI}

# =============================================================================
# OPENAI API CONFIGURATION
# =============================================================================
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=1000
# Inbound mailbox AI cost gate (default off). When enabled, ``orchestrate_incoming``
# applies the same ``ai_responses`` tier cap and AI budget guardrails as ``/ai/analyze-email``,
# and records usage after a successful analyze. See ``core/email_pipeline_ai_gate.py``.
# FIKIRI_EMAIL_PIPELINE_AI_GATE=1

# =============================================================================
# REDIS CONFIGURATION
# =============================================================================
# Option A: Full URL (works for Upstash or any Redis)
REDIS_URL=redis://localhost:6379/0

# Option B: Upstash-only — set these and REDIS_URL is derived automatically
# UPSTASH_REDIS_REST_URL=https://YOUR-INSTANCE.upstash.io
# UPSTASH_REDIS_REST_TOKEN=your-rest-token

REDIS_SESSION_URL=${REDIS_URL}
REDIS_CACHE_URL=${REDIS_URL}
REDIS_QUEUE_URL=${REDIS_URL}

# =============================================================================
# MICROSOFT GRAPH (OPTIONAL)
# =============================================================================
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret
MICROSOFT_TENANT_ID=your-microsoft-tenant-id

# =============================================================================
# ENCRYPTION & SECURITY
# =============================================================================
FERNET_KEY=your-32-byte-base64-encoded-key
FRONTEND_URL=https://fikirisolutions.com

# =============================================================================
# ANALYTICS & MONITORING
# =============================================================================
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project
SENTRY_DSN_WEBHOOKS=${SENTRY_DSN}
FLASK_ENVIRONMENT=production

# =============================================================================
# FEATURE FLAGS
# =============================================================================
LOG_LEVEL=INFO
ENABLE_CACHE=true
ENABLE_EMAIL_JOBS=true
ENABLE_RATE_LIMITING=true
EMAIL_TEMPLATES_ENABLED=true
```

## Render Deployment Configuration

```yaml
# render.yaml
services:
  - type: web
    name: fikiri-backend
    env: python
    plan: starter
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn --workers 2 --bind 0.0.0.0:$PORT app:app
    healthCheckPath: /health
    envVars:
      - key: FLASK_ENV
        value: production
      - key: DATABASE_URL
        fromService:
          type: pserv
          name: fikiri-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          type: redis
          name: fikiri-redis
          property: connectionString
```

## Feature Flag Status

| Feature | Environment Variable | Status |
|---------|---------------------|---------|
| AI Assistant | `OPENAI_API_KEY` | ✅ Enabled if set |
| Gmail OAuth | `GOOGLE_CLIENT_ID` | ✅ Required |
| Token Encryption | `FERNET_KEY` | ⚠️ Optional (falls back to plain) |
| Redis Cache | `REDIS_URL` | ⚠️ Optional (fallback to memory) |
| Microsoft Graph | `MICROSOFT_CLIENT_ID` | ❌ Disabled if missing |
| Sentry Monitoring | `SENTRY_DSN` | ⚠️ Optional | 
| Rate Limiting | `ENABLE_RATE_LIMITING` | ✅ Enabled by default |
| Mailbox AI cost gate | `FIKIRI_EMAIL_PIPELINE_AI_GATE` | ⚪ Off unless set to `1` / `true` / `yes` / `on` |

Related AI spend knobs (see `core/ai_budget_guardrails.py`, `core/tier_usage_caps.py`): `AI_BUDGET_*_USD`, `AI_ESTIMATED_COST_PER_RESPONSE_USD`, and model overrides `FIKIRI_LLM_MODEL_*` in `core/ai/model_policy.py`.

## Required vs Optional Services

### ✅ Required for Production
- `GOOGLE_CLIENT_ID` & `GOOGLE_CLIENT_SECRET`
- `DATABASE_URL`
- `FLASK_SECRET_KEY`

### ⚠️ Highly Recommended
- `OPENAI_API_KEY` (AI features)
- `REDIS_URL` (Performance)
- `FERNET_KEY` (Security)
- `SENTRY_DSN` (Monitoring)

### ❌ Optional
- `MICROSOFT_CLIENT_ID` (Office integration)
- `FIKIRI_EMAIL_PIPELINE_AI_GATE` (inbound mailbox AI tier + budget enforcement; default off)
- Features fall back gracefully
