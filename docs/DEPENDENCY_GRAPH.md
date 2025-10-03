# 🌳 Dependency Graph

## Core Module Dependencies

```
app.py (250 lines)
├── Imports from core/
│   ├── core.minimal_config
│   ├── core.minimal_auth  
│   ├── core.jwt_auth
│   ├── core.secure_sessions
│   ├── core.oauth_token_manager
│   └── core.monitoring
├── Imports from routes/
│   ├── routes.auth_bp
│   ├── routes.business_bp
│   ├── routes.test_bp
│   ├── routes.user_bp
│   └── routes.monitoring_bp
└── Blueprint registration
```

## Routes Module Dependencies

```
routes/auth.py
├── core.user_auth (user creation/authentication)
├── core.jwt_auth (token generation)
├── core.secure_sessions (session management)
├── core.api_validation (request validation)
├── core.rate_limiter (rate limiting)
├── core.enterprise_logging (security logs)
└── core.business_operations (analytics)

routes/business.py
├── core.enhanced_crm_service (CRM features)
├── core.automation_engine (automation rules)
├── core.automation_safety (safety checks)
├── core.oauth_token_manager (Gmail status)
├── core.secure_sessions (user ID)
└── core.database_optimization (queries)

routes/test.py
├── core.user_auth (create test users)
├── core.minimal_ai_assistant (AI testing)
├── core.minimal_email_parser (parser testing)
├── core.minimal_email_actions (action testing)
├── core.enhanced_crm_service (CRM testing)
└── core.oauth_token_manager (OAuth testing)

routes/user.py
├── core.user_auth (profile management)
├── core.secure_sessions (current user)
├── core.database_optimization (user queries)
├── core.automation_safety (automation status)
└── core.oauth_token_manager (connection status)

routes/monitoring.py
├── core.monitoring (health checks)
├── core.database_optimization (DB health)
├── core.oauth_token_manager (service status)
├── core.rate_limiter (rate limit status)
└── core.performance_monitor (metrics)
```

## Service Initialization Files

### Core Service Initializers
1. **`core/user_auth.py`** - User management & authentication
2. **`core/oauth_token_manager.py`** - OAuth token storage
3. **`core/secure_sessions.py`** - Session management
4. **`core/jwt_auth.py`** - JWT token generation
5. **`core/database_optimization.py`** - Database queries
6. **`core/monitoring.py`** - Health checks & monitoring

### Job & Background Service Managers
1. **`core/email_jobs.py`** - Email queue processing  
2. **`core/redis_queues.py`** - Background job queues
3. **`core/authentication_backup.py`** - Backup/restore jobs
4. **`core/onboarding_jobs.py`** - Onboarding sync jobs

### Token Managers
1. **`core/oauth_token_manager.py`** - Google OAuth tokens
   - Encrypts/decrypts tokens
   - Manages refresh cycles
   - Validates token expiry

## Import Resolution Order

```
1. Environment (.env)
2. Sentry (optional)
3. Flask app creation
4. Core service imports
5. Enhanced service imports  
6. Blueprint imports
7. Route blueprint imports
8. Service initialization
9. Health monitoring setup
10. Blueprint registration
11. app.run()
```

## Dependency Hierarchy

```
Level 1 (No dependencies):
├── core.minimal_config
├── core.database_optimization
└── environment variables

Level 2 (Depends on Level 1):
├── core.user_auth
├── core.minimal_auth
└── core.enteprise_logging

Level 3 (Depends on Level 1-2):
├── core.jwt_auth
├── core.secure_sessions
└── core.oauth_token_manager

Level 4 (Depends on Level 1-3):
├── routes/auth.py
├── routes/user.py
└── core.app_oauth

Level 5 (Depends on Level 1-4):
├── routes/business.py
├── routes/test.py
│       
└── routes/monitoring.py

Level 6 (Application Level):
└── app.py
```

## Circular Dependency Prevention

These modules are designed to avoid circular imports:
- **`core/user_auth`** - Does NOT import routes
- **`core/oauth_token_manager`** - Independent of auth flow
- **Routes modules** - Never import each other
- **`app.py`** - Only imports, never exports to core modules
