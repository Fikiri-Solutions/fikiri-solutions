# 🛠️ Troubleshooting Guide

## Common Issues & Direct Fixes

### Issue: "❌ BROKEN IMPORT: No module named 'core.x'"
**Cause**: Missing dependency or module deleted
**Fix**: 
```bash
# Check if module exists
ls core/ | grep missing_module

# Verify import path
python -c "import core.module_name"

# Fix broken import (likely in another file)
grep -r "from core.missing_module" .
```

### Issue: "⚠️ Token encryption disabled"
**Root Cause**: Missing `FERNET_KEY` or cryptography package
**Fix**:
```bash
# Add to .env
echo "FERNET_KEY=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" >> .env

# Install cryptography
pip install cryptography
```

### Issue: "⚠️ Redis URL not configured"
**Root Cause**: Missing `REDIS_URL`  
**Fix**:
```bash
# Add Redis URL to .env
echo "REDIS_URL=redis://localhost:6379/0" >> .env

# Or use Redis Cloud free tier
REDIS_URL=redis://user:pass@host:port
```

### Issue: "❌ Database connection failed"
**Root Cause**: Invalid `DATABASE_URL`
**Fix**:
```bash
# For SQLite
echo "DATABASE_URL=sqlite:///app.db" >> .env

# For PostgreSQL (Render)
echo "DATABASE_URL=postgresql://user:pass@host:5432/db" >> .env
```

### Issue: "❌ OAuth blueprint failed"
**Root Cause**: Missing Google OAuth credentials
**Fix**:
```bash
# Add to .env (get from Google Cloud Console)
echo "GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com" >> .env
echo "GOOGLE_CLIENT_SECRET=your-client-secret" >> .env
echo "GOOGLE_REDIRECT_URI=https://yourdomain.com/api/oauth/gmail/callback" >> .env
```

## Service Initialization Debugging

### Check Service Init Order
```python
# Add debug prints to see init order
python -c "
import sys; sys.path.append('.')
print('1. Environment loaded')
from core.user_auth import user_auth_manager; print('2. User auth loaded')
from core.oauth_token_manager import oauth_token_manager; print('3. OAuth manager loaded')  
from app import app; print('4. App initialized')
"
```

### Verify Blueprint Registration
```python
# Check which blueprints are registered
python -c "
from app import app
for module in app.blueprints:
    print(f'✅ Blueprint: {module}')
"
```

## OAuth Flow Debugging

### Test OAuth Start
```bash
curl -X POST https://fikirisolutions.com/api/oauth/gmail/start
# Should return: {"url": "https://accounts.google.com/o/oauth2/auth/..."}
```

### Check OAuth Credentials
```bash
python -c "
import os
print(f'GOOGLE_CLIENT_ID: {\"✅ Set\" if os.getenv(\"GOOGLE_CLIENT_ID\") else \"❌ Missing\"}')
print(f'GOOGLE_CLIENT_SECRET: {\"✅ Set\" if os.getenv(\"GOOGLE_CLIENT_SECRET\") else \"❌ Missing\"}')
print(f'GOOGLE_REDIRECT_URI: {\"✅ Set\" if os.getenv(\"GOOGLE_REDIRECT_URI\") else \"❌ Missing\"}')
"
```

## Database Schema Issues

### Verify Tables Exist
```python
python -c "
from core.database_optimization import db_optimizer
tables = db_optimizer.execute_query(\"SELECT name FROM sqlite_master WHERE type='table'\")
print('Tables:', [table['name'] for table in tables])
"
```

### Check Missing Migrations
```bash
# If schema changed, recreate tables
python -c "
from core.database_optimization import db_optimizer
# Drop and recreate critical tables
"
```

## Performance Debugging

### Check Redis Connection
```python
python -c "
from core.redis_cache import get_cache
try:
    cache = get_cache()
    cache.set('test', 'value')
    print('✅ Redis: Working')
except Exception as e:
    print(f'⚠️ Redis: {e}')
"
```

### Memory Usage Check
```bash
# Check memory consumption
ps aux | grep python | grep app.py
```

## Health Check Debugging

### Test Individual Endpoints
```bash
# Test health endpoint
curl https://fikirisolutions.com/health

# Test comprehensive health
curl https://fikirisolutions.com/api/health-old

# Test specific service
curl https://fikirisolutions.com/api/monitoring/gmail/status
```

## Quick Diagnostic Script

```bash
#!/bin/bash
echo "🔍 Fikiri Diagnostics"
echo "===================="

echo "📁 Files:"
ls -la app.py routes/ | grep -E "\.(py)$"

echo "🔧 Environment:"
python -c "
import os
required = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'DATABASE_URL']
for var in required:
    print(f'{var}: {\"✅\" if os.getenv(var) else \"❌\"}')
"

echo "🚀 App Import:"
python -c "
try:
    from app import app
    print('✅ App imports successfully')
except Exception as e:
    print(f'❌ Import failed: {e}')
"

echo "❤️ Health Check:"
python -c "
try:
    from app import app
    with app.test_client() as client:
        response = client.get('/health')
        print(f'✅ Health endpoint: {response.status_code}')
except Exception as e:
    print(f'❌ Health check failed: {e}')
"
```

## Emergency Fixes

### Reset to Clean State
```bash
# Backup current state
cp app.py app_backup_$(date +%Y%m%d_%H%M%S).py

# Reset to working version
git checkout HEAD~1 -- app.py

# Or restore from backup
cp app_original_backup.py app.py
```

### Manual Service Restart
```bash
# Kill existing processes
pkill -f "python.*app.py"

# Restart clean
python app.py
```
