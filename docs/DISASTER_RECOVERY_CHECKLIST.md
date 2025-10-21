# Fikiri Solutions Disaster Recovery Checklist

## 🚨 Emergency Recovery Procedures

### 1. Environment Variables Backup
```bash
# Critical environment variables to backup
JWT_SECRET_KEY=xbppiUtMLEy-edconosX09sfeaeGwMhmhCxFabteQtw
FERNET_KEY=2HJ-fbPvowR0BFd7MR2nXO4REdtRtBoz4Bb-HFTl4aU=
REDIS_URL=redis://default:fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H@redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com:19575
```

### 2. Database Recovery
```bash
# Export current database
sqlite3 data/fikiri.db ".dump" > backup/fikiri_backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
sqlite3 data/fikiri.db < backup/fikiri_backup_YYYYMMDD_HHMMSS.sql
```

### 3. Redis Recovery
```bash
# Redis Cloud connection string (backup)
redis://default:fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H@redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com:19575

# Test connection
redis-cli -u redis://default:fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H@redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com:19575 ping
```

### 4. Application Recovery
```bash
# Quick restart procedure
git clone https://github.com/Fikiri-Solutions/fikiri-solutions.git
cd fikiri-solutions
cp env.template .env
# Add environment variables from backup
pip install -r requirements.txt
python app.py
```

### 5. Frontend Recovery
```bash
cd frontend
npm install
npm run build
# Deploy to Vercel or serve locally
```

## 🔄 Quarterly Security Hygiene Checklist

### Every ~90 Days:

#### 1. Key Rotation
```bash
# Generate new JWT secret
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate new Fernet key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

#### 2. Session Cleanup
```bash
# Flush all Redis sessions
redis-cli -u $REDIS_URL FLUSHDB

# Or selective cleanup
redis-cli -u $REDIS_URL --scan --pattern "session:*" | xargs redis-cli -u $REDIS_URL DEL
```

#### 3. Certificate Verification
```bash
# Check HTTPS certificates
openssl s_client -connect fikirisolutions.com:443 -servername fikirisolutions.com
```

#### 4. Dependency Audit
```bash
# Python dependencies
pip-audit

# Node.js dependencies
cd frontend && npm audit
```

#### 5. Security Scan
```bash
# Run security tests
./scripts/smoke_test.sh
python -m pytest tests/security/
```

## 📊 Monitoring Alerts Setup

### Critical Alerts:
- `auth_login_failed_total` > 100 in 5 minutes
- `redis_connection_errors_total` > 0
- `database_query_duration_seconds` > 5 seconds
- `jwt_token_generation_duration_seconds` > 1 second

### Warning Alerts:
- `active_sessions_total` drops by 50%
- `api_requests_per_minute` drops by 80%
- `onboarding_completion_rate` < 0.7

## 🛡️ Security Hardening Checklist

### Rate Limiting
```python
# Add to auth endpoints
@limiter.limit("5 per minute")
def login():
    pass
```

### CSRF Protection
```python
# For non-REST pages
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)
```

### WebAuthn Integration
```javascript
// For premium users
navigator.credentials.create({
    publicKey: {
        challenge: new Uint8Array(32),
        rp: { name: "Fikiri Solutions" },
        user: { id: new Uint8Array(16), name: "user@example.com" },
        pubKeyCredParams: [{ type: "public-key", alg: -7 }]
    }
});
```

### Session Anomaly Detection
```python
# Alert on new IP/device
if user.last_ip != request.remote_addr:
    send_security_alert(user, "New IP address detected")
```

## 📋 Pre-Deployment Checklist

### Before Each Deploy:
- [ ] Run `./scripts/smoke_test.sh`
- [ ] Check Playwright screenshots for 401 loops
- [ ] Verify cookies in DevTools (Safari + Chrome)
- [ ] Test CORS with different origins
- [ ] Validate JWT token expiration
- [ ] Check Redis connection stability
- [ ] Verify database migrations
- [ ] Test frontend compilation
- [ ] Run security audit
- [ ] Check environment variables

### Post-Deploy Verification:
- [ ] Health check endpoint responds
- [ ] Login flow works end-to-end
- [ ] Token refresh works
- [ ] Cookies set correctly
- [ ] CORS headers present
- [ ] Database queries execute
- [ ] Redis operations work
- [ ] Frontend loads correctly
- [ ] No console errors
- [ ] Performance metrics normal

## 🚀 Quick Recovery Commands

```bash
# Full system restart
pkill -f "python app.py" && pkill -f "npm run dev"
python app.py &
cd frontend && npm run dev &

# Database integrity check
python -c "from core.database_optimization import db_optimizer; db_optimizer._check_database_integrity()"

# Redis connection test
python -c "import redis; r = redis.from_url('$REDIS_URL'); print(r.ping())"

# JWT token test
python -c "from core.jwt_auth import get_jwt_manager; jwt = get_jwt_manager(); print(jwt.generate_tokens(1, {'test': 'data'}))"
```
