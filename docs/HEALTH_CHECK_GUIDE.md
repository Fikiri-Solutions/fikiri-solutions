# ❤️ Health Check Guide

## Expected Startup Logs (Clean Run)

```
✅ Sentry initialized successfully
📊 Redis connection: Available  
✅ Health monitoring initialized  
🏗️ Core services initialized successfully  
✅ OAuth blueprint registered  
✅ Onboarding blueprint registered  
✅ All blueprints registered  
🚀 Server starting on 0.0.0.0:5000  
```

## API Health Check Response

### `/health` Endpoint
```json
{
  "status": "running",
  "timestamp": "2024-01-15T10:30:00.123456",
  "version": "1.0.0",
  "message": "Fikiri Solutions API",
  "endpoints": {
    "auth": "/api/auth/*",
    "business": "/api/business/*", 
    "test": "/api/test/*",
    "user": "/api/user/*",
    "monitoring": "/api/monitoring/*",
    "health": "/api/health"
  },
  "frontend": "https://fikirisolutions.com"
}
```

### `/api/health-old` (Comprehensive)
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.123456", 
  "version": "1.0.0",
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5,
      "error": null
    },
    "redis": {
      "status": "healthy", 
      "response_time_ms": 3,
      "error": null
    },
    "gmail_auth": {
      "status": "configured",
      "response_time_ms": 15,
      "error": null
    },
    "openai": {
      "status": "configured",
      "response_time_ms": 20,
      "error": null
    }
  },
  "metrics": {
    "uptime": "operational",
    "active_users": 0,
    "active_connections": 1,
    "initialized_services": 6
  },
  "environment": "production"
}
```

## Warning Signs to Watch For

### 🚨 Critical Errors
```
❌ BROKEN IMPORT: No module named 'core.x'
❌ Database connection failed
❌ OAuth blueprint failed
❌ Internal server error
```

### ⚠️ Non-Critical Warnings
```
⚠️ Token encryption disabled (missing cryptography or FERNET_KEY)
⚠️ Redis URL not configured  
⚠️ OpenAI API key not found - AI features will be disabled
⚠️ Sentry initialization failed
```

### ✅ Acceptable Logs
```
✅ All services initialized successfully
✅ Health monitoring initialized
✅ OAuth blueprint registered
✅ Loaded 6 leads from data/leads.json
📝 No vector database found (runs once)
```

## Integration Test Examples

### 1. OAuth Test
```python
# Should return: {"url": "https://accounts.google.com/o/oauth2/auth/..."}
POST /api/oauth/gmail/start
Response: 200 OK
{"url": "https://accounts.google.com/o/oauth2/..."}
```

### 2. Signup Test  
```python
# Should return: {"user": {"id": 123, "email": "..."}, "success": true}
POST /api/auth/signup
Body: {"email": "test@example.com", "password": "testpass123", "name": "Test"}
Response: 200 OK
{"user": {"id": 123, "email": "test@example.com"}, "success": true}
```

### 3. Health Test
```python
# Should return: {"status": "running", ...}
GET /health  
Response: 200 OK
{"status": "running", "timestamp": "2024-01-15..."}
```

## Debug Commands

### Quick Health Check
```bash
curl https://fikirisolutions.com/health
```

### Service Status
```bash  
python -c "
import sys; sys.path.append('.')
from app import app
print('✅ App imports successfully')
"
```

### Redis Test
```python
python -c "
import redis
from core.redis_cache import get_cache
try:
    cache = get_cache()
    print('✅ Redis: Connected')
except:
    print('⚠️ Redis: Fallback to memory')
"
```
