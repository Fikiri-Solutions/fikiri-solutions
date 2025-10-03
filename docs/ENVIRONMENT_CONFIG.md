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

# =============================================================================
# REDIS CONFIGURATION
# =============================================================================
REDIS_URL=redis://localhost:6379/0
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
- `MICREOSOFT_CLIENT_ID` (Office integration)
- Features fall back gracefully
