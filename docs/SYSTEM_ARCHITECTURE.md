# 🏗️ Fikiri Solutions Architecture

## System Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ React/Vercel    │◄──►│ Flask/Render    │◄──►│ SQLite/Render   │
│ https://fikiri- │    │ gunicorn        │    │ Users, OAuth    │
│ solutions.com   │    │ Health checks   │    │ Sessions        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   External APIs │    │   Redis Services│    │   File Storage  │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ Google OAuth    │◄──►│ Redis Cloud     │    │ Render Disk     │
│ OpenAI API      │    │ Sessions        │    │ Logs, temp      │
│ Sentry          │    │ Cache, Queues   │    │                
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Data Flow: OAuth/Onboarding

```
1. User clicks "Sign up with Gmail"
   ↓
2. Frontend → POST /api/oauth/gmail/start
   ↓
3. Backend generates OAuth URL + state
   ↓
4. Frontend redirects to Google OAuth
   ↓
5. Google → POST /oauth/callback?code=...
   ↓
6. Backend exchanges code for tokens
   ↓
7. Store tokens in database
   ↓
8. Create user record
   ↓
9. Return JWT token + session cookie
   ↓
10. Frontend stores token, redirects to onboarding
```

## Flask Blueprint Map

```
app.py (250 lines - Main)
├── routes/auth.py (293 lines)
│   ├── /api/auth/login
│   ├── /api/auth/signup
│   ├── /api/auth/forgot-password
│   └── /api/auth/reset-password

├── routes/business.py (374 lines)
│   ├── /api/crm/* (leads, pipeline)
│   ├── /api/automation/* (rules, execute)
│   ├── /api/gmail/sync

├── routes/test.py (282 lines)
│   ├── /api/test/debug
│   ├── /api/test/email-parser
│   ├── /api/test/ai-assistant
│   └── /api/test/openai-key

├── routes/user.py (244 lines)
│   ├── /api/user/profile
│   ├── /api/user/onboarding-step
│   ├── /api/user/dashboard-data
│   └── /api/user/export-data

├── routes/monitoring.py (279 lines)
│   ├── /health
│   ├── /api/monitoring/gmail/status
│   ├── /api/monitoring/system/metrics
│   └── /api/monitoring/alerts

├── Core Blueprints:
│   ├── core/app_oauth → /api/oauth/*
│   ├── core/app_onboarding → /api/onboarding/*
│   ├── core/billing_api → /api/billing/*
│   ├── core/webhook_api → /api/webhooks/*
│   ├── core/crm_completion_api → /api/crm/* (complement)
│   └── analytics/monitoring_api → /api/monitoring/*
```

## Service Initialization Order

```
1. Environment Variables (.env)
2. Sentry (error tracking)
3. Flask App + CORS
4. Core Services (MinimalAuth, Gmail, CRM, AI)
5. Enhanced Services (JWT, Secure Sessions)
6. Database Optimization
7. Redis Services (Cache, Sessions, Queues)
8. Monitoring (Health checks)
9. Blueprint Registration
10. App.run()
```