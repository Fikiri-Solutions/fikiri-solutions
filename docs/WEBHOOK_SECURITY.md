# Webhook Security & Production Readiness

**Date:** February 2026  
**Status:** ✅ Implemented

---

## Security Features Implemented

### 1. ✅ API Key Authentication
- All webhook endpoints require `X-API-Key` header
- Keys are validated against database
- Invalid/expired keys are rejected

### 2. ✅ Scope-Based Permissions
- API keys have scoped permissions
- Webhook endpoints check for required scopes:
  - `/api/webhooks/forms/submit` requires: `webhooks:forms` or `leads:create`
  - `/api/webhooks/leads/capture` requires: `webhooks:leads` or `leads:create`
- Wildcard scopes (`webhooks:*`, `leads:*`) are supported

### 3. ✅ Origin Allowlist (Optional)
- API keys can have `allowed_origins` configured
- If configured, webhook endpoints validate `Origin` header
- Requests from non-allowed origins are rejected
- **Note:** Origin validation is optional - if `allowed_origins` is null/empty, all origins are allowed

### 4. ✅ Idempotency
- All webhook endpoints use idempotency keys
- Prevents duplicate submissions
- Idempotency keys are generated deterministically from:
  - Operation type
  - User ID
  - Email (normalized to lowercase)
  - Form ID / Source
- Duplicate requests return cached response with `deduplicated: true`

### 5. ✅ Response Contract
- All webhook responses include:
  - `success`: Boolean indicating success/failure
  - `lead_id`: ID of created lead (if successful)
  - `deduplicated`: Boolean indicating if request was deduplicated
  - `idempotency_key`: Partial idempotency key (first 16 chars) for debugging
  - `error`: Error message (if failed)
  - `error_code`: Machine-readable error code

---

## API Versioning

**Current Status:** Endpoints are not versioned (using `/api/webhooks/...`)

**Recommendation:** For production, consider versioning:
- `/api/v1/webhooks/forms/submit`
- `/api/v1/webhooks/leads/capture`

**Migration Path:** When v2 is needed:
1. Add new endpoints with `/api/v2/...`
2. Keep v1 endpoints active for backward compatibility
3. Deprecate v1 after migration period

---

## Example Responses

### Success Response (New Submission)
```json
{
  "success": true,
  "lead_id": 123,
  "message": "Form submitted successfully",
  "deduplicated": false,
  "idempotency_key": "abc123def4567890..."
}
```

### Success Response (Duplicate)
```json
{
  "success": true,
  "lead_id": 123,
  "message": "Form submitted successfully",
  "deduplicated": true,
  "idempotency_key": "abc123def4567890..."
}
```

### Error Response (Missing API Key)
```json
{
  "success": false,
  "error": "API key required (X-API-Key header)",
  "error_code": "MISSING_API_KEY"
}
```

### Error Response (Invalid Scope)
```json
{
  "success": false,
  "error": "Insufficient permissions. Required scope: webhooks:forms or leads:create",
  "error_code": "INSUFFICIENT_SCOPE"
}
```

### Error Response (Origin Not Allowed)
```json
{
  "success": false,
  "error": "Origin not allowed",
  "error_code": "ORIGIN_NOT_ALLOWED"
}
```

---

## Configuration

### Creating API Keys with Scopes

```python
from core.api_key_manager import api_key_manager

# Create API key with webhook permissions
result = api_key_manager.generate_api_key(
    user_id=1,
    name="Website Integration",
    scopes=["webhooks:forms", "webhooks:leads", "chatbot:query"],
    allowed_origins=["https://example.com", "https://www.example.com"],  # Optional
    rate_limit_per_minute=60,
    rate_limit_per_hour=1000
)
```

### Creating API Keys with Origin Restrictions

```python
# Restrict to specific domains
result = api_key_manager.generate_api_key(
    user_id=1,
    name="Production Website",
    scopes=["webhooks:*"],
    allowed_origins=[
        "https://mywebsite.com",
        "https://www.mywebsite.com"
    ]
)

# Allow all origins (default)
result = api_key_manager.generate_api_key(
    user_id=1,
    name="Development",
    scopes=["webhooks:*"],
    allowed_origins=None  # or []
)
```

---

## Best Practices

### 1. Use Appropriate Scopes
- Don't grant `webhooks:*` unless necessary
- Use specific scopes: `webhooks:forms`, `webhooks:leads`

### 2. Configure Origin Restrictions
- For production, restrict API keys to specific domains
- Use `allowed_origins` to prevent unauthorized usage

### 3. Handle Idempotency
- Always check `deduplicated` flag in responses
- Use idempotency keys for retry logic
- Don't treat deduplicated responses as errors

### 4. Error Handling
- Check `error_code` for programmatic error handling
- Log `idempotency_key` for debugging duplicate submissions
- Implement retry logic with exponential backoff

### 5. Rate Limiting
- Respect rate limits (60/min, 1000/hour by default)
- Implement client-side rate limiting
- Handle 429 (Too Many Requests) responses gracefully

---

## Testing

### Test Idempotency
```bash
# First request
curl -X POST https://api.fikirisolutions.com/api/webhooks/leads/capture \
  -H "X-API-Key: fik_xxx" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "name": "Test"}'

# Duplicate request (should return deduplicated: true)
curl -X POST https://api.fikirisolutions.com/api/webhooks/leads/capture \
  -H "X-API-Key: fik_xxx" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "name": "Test"}'
```

### Test Scope Enforcement
```bash
# Request with insufficient scope (should fail)
curl -X POST https://api.fikirisolutions.com/api/webhooks/forms/submit \
  -H "X-API-Key: fik_key_without_webhook_scope" \
  -H "Content-Type: application/json" \
  -d '{"fields": {"email": "test@example.com"}}'
```

### Test Origin Restriction
```bash
# Request from allowed origin (should succeed)
curl -X POST https://api.fikirisolutions.com/api/webhooks/leads/capture \
  -H "X-API-Key: fik_xxx" \
  -H "Origin: https://example.com" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Request from disallowed origin (should fail)
curl -X POST https://api.fikirisolutions.com/api/webhooks/leads/capture \
  -H "X-API-Key: fik_xxx" \
  -H "Origin: https://malicious.com" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

---

*Last updated: February 2026*
