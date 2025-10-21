# Fikiri Solutions Authentication Debug Guide

## 🔧 Common Authentication Issues & Solutions

This guide addresses the most common authentication problems encountered in Flask/JWT applications, based on Stack Overflow consensus and production experience.

## 🚨 Critical Issues Fixed

### 1. JWT Secret Key Persistence ✅ FIXED
**Problem**: Tokens become invalid after server restart
**Root Cause**: JWT manager instantiated before environment variables loaded
**Solution**: Implemented lazy loading pattern

```python
# Before (BROKEN)
jwt_auth_manager = JWTAuthManager()  # Instantiated at import time

# After (FIXED)
def get_jwt_manager():
    global jwt_auth_manager
    if jwt_auth_manager is None:
        jwt_auth_manager = JWTAuthManager()
    return jwt_auth_manager
```

### 2. Password Hashing Consistency ✅ VERIFIED
**Problem**: Signup works but login fails with "Invalid credentials"
**Root Cause**: Mismatched hashing algorithms or salt handling
**Solution**: Consistent PBKDF2 with SHA-256

```python
def _hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
    """Hash password with salt using PBKDF2"""
    if salt is None:
        salt = secrets.token_hex(self.salt_length)
    
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000  # 100,000 iterations
    )
    
    return password_hash.hex(), salt
```

### 3. CORS Configuration ✅ VERIFIED
**Problem**: Login works via cURL but fails in browser
**Root Cause**: Missing or incorrect CORS headers
**Solution**: Proper CORS configuration

```python
CORS(app, 
     resources={r"/api/*": {"origins": [
         "https://fikirisolutions.com",
         "http://localhost:3000"
     ]}},
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
     supports_credentials=True,
     max_age=3600
)
```

### 4. Database Race Conditions ✅ PREVENTED
**Problem**: Login fails right after deploy because user table isn't ready
**Root Cause**: Workers start before database schema is initialized
**Solution**: Prestart script with lock mechanism

```python
def create_init_lock(db_path):
    """Create initialization lock to prevent double initialization."""
    lock_path = Path(db_path).parent / ".db_init_lock"
    if lock_path.exists():
        return True
    
    lock_path.write_text(f"initialized_at={time.time()}")
    return False
```

### 5. Token Validation Issues ✅ FIXED
**Problem**: "Token is not yet valid (iat)" errors
**Root Cause**: `datetime.utcnow()` deprecation causing timezone issues
**Solution**: Use `datetime.now()` for consistent time handling

```python
# Before (BROKEN)
current_time = datetime.utcnow()

# After (FIXED)
current_time = datetime.now()
```

## 🔍 Debugging Checklist

### Step 1: Verify Database Seed
```bash
python -c "
from core.database_optimization import db_optimizer
users = db_optimizer.execute_query('SELECT COUNT(*) as count FROM users')
print(f'Users in database: {users[0][\"count\"]}')
"
```

### Step 2: Confirm Password Hashing
```bash
python -c "
from core.user_auth import UserAuthManager
auth_manager = UserAuthManager()
test_password = 'test123'
hash_result, salt = auth_manager._hash_password(test_password)
is_valid = auth_manager._verify_password(test_password, hash_result, salt)
print(f'Password verification: {is_valid}')
"
```

### Step 3: Decode JWT Token
```bash
python -c "
from core.jwt_auth import get_jwt_manager
jwt_manager = get_jwt_manager()
tokens = jwt_manager.generate_tokens(1, {'id': 1, 'email': 'test@example.com'})
verified = jwt_manager.verify_access_token(tokens['access_token'])
print(f'Token verification: {verified is not None}')
"
```

### Step 4: Inspect Network Tab
- Check for 401/403 errors in browser console
- Verify CORS headers in response
- Confirm Authorization header format: `Bearer <token>`

### Step 5: Cross-Environment Test
- Test local vs deployed database paths
- Verify environment variables are loaded correctly
- Check Redis connection for session storage

## 🏗️ Architecture Patterns Implemented

### Auth Blueprint Structure
```
routes/auth.py
├── /api/auth/signup → hash + store + send verification
├── /api/auth/login → verify + issue JWT (access + refresh)
└── /api/auth/refresh → rotate refresh tokens
```

### Middleware Pattern
```python
@jwt_required
def protected_route():
    # Token verification handled by decorator
    user = get_current_user()
    return jsonify(user)
```

### Onboarding State Management
```python
# Server-side onboarding progress
users.onboarding_step INTEGER DEFAULT 1
users.onboarding_completed BOOLEAN DEFAULT FALSE

# Frontend routing based on onboarding state
if user.onboarding_completed:
    navigate('/dashboard')
else:
    navigate('/onboarding')
```

## 🔒 Security Best Practices

### Password Security
- ✅ PBKDF2 with 100,000 iterations
- ✅ Random salt generation (32 bytes)
- ✅ Secure password comparison with `secrets.compare_digest`

### JWT Security
- ✅ Short-lived access tokens (15 minutes)
- ✅ Refresh token rotation
- ✅ Token blacklisting support
- ✅ Device-specific sessions

### Session Management
- ✅ Redis-backed sessions
- ✅ IP address tracking
- ✅ User agent validation
- ✅ Automatic cleanup of expired tokens

## 🚀 Production Deployment

### Environment Variables
```bash
# Required for production
JWT_SECRET_KEY=xbppiUtMLEy-edconosX09sfeaeGwMhmhCxFabteQtw
REDIS_URL=redis://your-redis-url
DATABASE_URL=postgresql://your-db-url
```

### Prestart Script
```bash
# Run before workers start
python scripts/prestart.py
```

### Health Checks
```bash
# Verify authentication system
curl -X POST http://localhost:5000/api/dev/jwt-stability-test
```

## 📊 Monitoring & Logging

### Authentication Metrics
- Login success/failure rates
- Token refresh frequency
- Session duration
- Failed login attempts

### Error Tracking
- JWT validation errors
- Password verification failures
- CORS policy violations
- Database connection issues

## 🧪 Testing Commands

### Test Complete Auth Flow
```bash
# 1. Create user
curl -X POST http://localhost:5000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","name":"Test User"}'

# 2. Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# 3. Use token
curl -X GET http://localhost:5000/api/dashboard \
  -H "Authorization: Bearer <access_token>"
```

### Test JWT Stability
```bash
python -c "
from core.jwt_auth import get_jwt_manager
jwt_manager = get_jwt_manager()
print(f'JWT Secret: {jwt_manager.secret_key[:20]}...')
print('JWT system ready ✅')
"
```

## 🎯 Next Steps

1. **Monitor Production**: Watch for authentication errors in logs
2. **Rate Limiting**: Implement per-user rate limits
3. **Multi-Factor Auth**: Add 2FA support for enterprise users
4. **Audit Logging**: Track all authentication events
5. **Token Refresh**: Implement automatic token refresh in frontend

---

*This guide addresses the most common authentication issues found in production Flask applications. All fixes have been tested and verified.*
