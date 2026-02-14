# Public API Testing Guide

## Overview

This document describes the unit tests created to verify the public API implementation works correctly in practice, not just in theory.

## Test Coverage

### 1. API Key Manager Tests (`test_api_key_manager.py`)

**Tests Created:**
- ✅ API key generation creates valid keys with correct format
- ✅ API key validation accepts correctly formatted keys
- ✅ API key validation rejects invalid/expired keys
- ✅ Tenant isolation works correctly
- ✅ Rate limit tracking and enforcement
- ✅ API key revocation
- ✅ Listing API keys for a user
- ✅ Custom scopes support
- ✅ Custom rate limits support

**What It Verifies:**
- Keys are generated securely (SHA-256 hashed)
- Keys follow the `fik_` prefix format
- Expiration logic works
- Tenant isolation prevents cross-tenant access
- Rate limiting tracks usage correctly
- Keys can be revoked and become invalid

### 2. Public Chatbot API Tests (`test_public_chatbot_api.py`)

**Tests Created:**
- ✅ Query endpoint requires API key
- ✅ Query endpoint rejects invalid API keys
- ✅ Query endpoint works with valid key
- ✅ Rate limit enforcement (429 responses)
- ✅ Missing query parameter validation
- ✅ Health endpoint doesn't require auth
- ✅ CORS headers present
- ✅ Bearer token authentication format

**What It Verifies:**
- Authentication decorator works correctly
- Invalid keys are rejected
- Valid requests process correctly
- Rate limits are enforced
- CORS is configured properly
- Error responses are consistent

### 3. AI Analysis API Tests (`test_ai_analysis_api.py`)

**Tests Created:**
- ✅ Contact analysis requires API key
- ✅ Schema validation rejects invalid data
- ✅ Contact analysis works with valid data
- ✅ Lead analysis works correctly
- ✅ Business analysis works correctly
- ✅ Invalid email format rejected

**What It Verifies:**
- Marshmallow schema validation works
- Required fields are enforced
- Email format validation works
- AI analysis endpoints return structured responses
- Error handling is consistent

### 4. Vector Persistence Tests (`test_vector_persistence.py`)

**Tests Created:**
- ✅ FAQ creation persists to vector index
- ✅ Knowledge document creation persists to vector index
- ✅ Vector persistence failure doesn't break FAQ creation

**What It Verifies:**
- Chatbot Builder properly indexes FAQs
- Knowledge base documents are indexed
- Graceful fallback if vectorization fails
- Metadata is preserved correctly

## Running Tests

### Run All Public API Tests

```bash
# From project root
python tests/run_public_api_tests.py
```

### Run Individual Test Files

```bash
# API Key Manager tests
python -m pytest tests/test_api_key_manager.py -v

# Public Chatbot API tests
python -m pytest tests/test_public_chatbot_api.py -v

# AI Analysis API tests
python -m pytest tests/test_ai_analysis_api.py -v

# Vector Persistence tests
python -m pytest tests/test_vector_persistence.py -v
```

### Run with unittest

```bash
python -m unittest tests.test_api_key_manager
python -m unittest tests.test_public_chatbot_api
python -m unittest tests.test_ai_analysis_api
python -m unittest tests.test_vector_persistence
```

## Test Results Interpretation

### Success Criteria

All tests should pass with:
- ✅ Green checkmarks for each test
- ✅ No errors or failures
- ✅ Exit code 0

### Common Issues

1. **Database Connection Errors**
   - Ensure test database is accessible
   - Check `FLASK_ENV=test` is set
   - Verify database tables exist

2. **Import Errors**
   - Ensure project root is in Python path
   - Check all dependencies are installed
   - Verify `marshmallow` is installed

3. **Mock Failures**
   - Check mock patches match actual import paths
   - Verify mock return values match expected types
   - Ensure mocks are cleaned up between tests

## Integration Testing

### Manual Integration Test

After unit tests pass, test the actual endpoints:

```bash
# 1. Start backend
python app.py

# 2. Generate API key (via Python console)
python -c "
from core.api_key_manager import api_key_manager
result = api_key_manager.generate_api_key(
    user_id=1,
    name='Test Key'
)
print('API Key:', result['api_key'])
"

# 3. Test chatbot query
curl -X POST http://localhost:5000/api/public/chatbot/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: fik_YOUR_KEY_HERE" \
  -d '{"query": "What are your hours?"}'

# 4. Test contact analysis
curl -X POST http://localhost:5000/api/public/ai/analyze/contact \
  -H "Content-Type: application/json" \
  -H "X-API-Key: fik_YOUR_KEY_HERE" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "company": "Acme Corp"
  }'
```

## Test Coverage Summary

| Component | Unit Tests | Integration Tests | Status |
|-----------|------------|-------------------|--------|
| API Key Manager | ✅ 10 tests | ⚠️ Manual | Ready |
| Public Chatbot API | ✅ 8 tests | ⚠️ Manual | Ready |
| AI Analysis API | ✅ 6 tests | ⚠️ Manual | Ready |
| Vector Persistence | ✅ 3 tests | ⚠️ Manual | Ready |

**Total: 27 unit tests covering critical paths**

## Next Steps

1. ✅ **Unit Tests Created** - All critical paths covered
2. ⚠️ **Run Tests** - Execute test suite to verify
3. ⚠️ **Fix Any Issues** - Address failures if found
4. ⚠️ **Integration Testing** - Test with real backend
5. ⚠️ **Load Testing** - Test rate limiting under load
6. ⚠️ **Security Testing** - Test authentication edge cases

## Continuous Integration

To add to CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Run Public API Tests
  run: |
    python tests/run_public_api_tests.py
```

## Notes

- Tests use mocks to avoid external dependencies
- Database cleanup happens in `tearDown()` methods
- Tests are isolated and can run in any order
- All tests use `FLASK_ENV=test` for test isolation
