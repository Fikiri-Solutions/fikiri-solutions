# 🚀 Fikiri Solutions - API Quick Reference

## Base URLs
- **Production**: https://fikirisolutions.com/api
- **Development**: http://localhost:8081/api

## Authentication
All protected endpoints require a valid session token.

## Common Response Format
```json
{
  "success": true|false,
  "data": {...},
  "message": "Success message",
  "timestamp": "2024-01-01T00:00:00Z",
  "error": "Error message (if success: false)",
  "code": "ERROR_CODE (if applicable)"
}
```

---

## 🔐 Authentication

### POST /auth/login
Login with email and password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "user_id",
      "email": "user@example.com",
      "name": "User Name",
      "role": "user"
    },
    "session_id": "session_token"
  }
}
```

### POST /auth/logout
Logout and invalidate session.

### GET /auth/status
Check authentication status.

---

## 👥 CRM

### GET /crm/leads
Get all leads.

**Response:**
```json
{
  "success": true,
  "data": {
    "leads": [...],
    "count": 42
  }
}
```

### POST /crm/leads
Add a new lead.

**Request:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+1234567890",
  "company": "Acme Corp",
  "notes": "Interested in premium plan"
}
```

**Validation:**
- `name`: Required, 1-100 characters
- `email`: Required, valid email format
- `phone`: Optional, valid phone format
- `company`: Optional, max 100 characters
- `notes`: Optional, max 1000 characters

---

## 🤖 AI Assistant

### POST /ai/chat
Send a message to the AI assistant.

**Request:**
```json
{
  "message": "Hello, how can you help me?",
  "context": {
    "conversation_history": []
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "response": "Hello! I can help you with...",
    "classification": {
      "intent": "general_inquiry",
      "confidence": 0.95
    },
    "action_taken": "provide_information"
  }
}
```

**Validation:**
- `message`: Required, 1-2000 characters
- `context`: Optional object

---

## 📊 Performance & Monitoring

### GET /performance/summary
Get comprehensive performance summary.

**Response:**
```json
{
  "success": true,
  "data": {
    "uptime_seconds": 86400,
    "requests": {
      "total_last_hour": 150,
      "avg_response_time": 0.245,
      "error_rate_percent": 0.5,
      "throughput_rpm": 2.5
    },
    "system": {
      "cpu_percent": 45.2,
      "memory_percent": 67.8,
      "disk_percent": 23.1
    },
    "endpoints": {
      "/api/auth/login": {
        "count": 25,
        "avg_time": 0.156,
        "error_count": 0
      }
    }
  }
}
```

### GET /performance/endpoint/{endpoint}
Get performance metrics for specific endpoint.

### GET /performance/system-health
Get current system health status.

### GET /performance/export?hours=24
Export performance metrics for analysis.

---

## 🏥 Health & Status

### GET /health
Comprehensive health check.

**Response:**
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0",
  "services": {
    "auth": {"status": "healthy", "available": true},
    "crm": {"status": "healthy", "available": true},
    "ai_assistant": {"status": "healthy", "available": true}
  }
}
```

### GET /services
Get all available services and their status.

### GET /metrics
Get dashboard metrics.

### GET /activity
Get recent activity feed.

---

## 🏭 Industry-Specific

### POST /industry/chat
Industry-specific AI chat.

**Request:**
```json
{
  "industry": "landscaping",
  "client_id": "client_123",
  "message": "I need help with lead management"
}
```

### GET /industry/prompts
Get available industry-specific prompts.

### GET /industry/analytics/{client_id}
Get client analytics and reporting.

### GET /industry/pricing-tiers
Get pricing tier information.

---

## 📈 Analytics

### POST /analytics/generate-report
Generate comprehensive client report.

### POST /analytics/roi-calculator
Calculate ROI for potential clients.

### GET /analytics/industry-benchmarks
Get industry benchmarks for comparison.

---

## 🧪 Testing Endpoints

### POST /test/email-parser
Test email parser with sample data.

### POST /test/email-actions
Test email actions.

### POST /test/crm
Test CRM service.

### POST /test/ai-assistant
Test AI assistant.

### POST /test/ml-scoring
Test ML scoring service.

### POST /test/vector-search
Test vector search service.

### GET /test/openai-key
Test OpenAI API key status.

---

## 📧 Email Services

### GET /email/providers
Get all available email providers and their status.

### POST /email/switch-provider
Switch to a different email provider.

### GET /email/messages?limit=10
Get recent messages from the active email provider.

### POST /email/send
Send an email via the active provider.

**Request:**
```json
{
  "to": "recipient@example.com",
  "subject": "Email Subject",
  "body": "Email body content"
}
```

---

## 🚨 Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Input validation failed |
| `AUTHENTICATION_REQUIRED` | Valid session required |
| `INVALID_CREDENTIALS` | Login credentials invalid |
| `SERVICE_UNAVAILABLE` | Required service not available |
| `AI_SERVICE_UNAVAILABLE` | AI assistant not available |
| `PERFORMANCE_ERROR` | Performance monitoring error |
| `INTERNAL_ERROR` | Internal server error |

---

## 📝 Rate Limits

- **Authentication**: 5 requests per minute per IP
- **AI Chat**: 10 requests per minute per user
- **CRM Operations**: 20 requests per minute per user
- **General API**: 100 requests per minute per IP

---

## 🔧 Development Tips

### Testing API Endpoints
```bash
# Health check
curl -X GET http://localhost:8081/api/health

# Login
curl -X POST http://localhost:8081/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Get leads
curl -X GET http://localhost:8081/api/crm/leads \
  -H "Cookie: session=your_session_token"
```

### Error Handling
Always check the `success` field in responses:
```javascript
const response = await fetch('/api/endpoint');
const data = await response.json();

if (data.success) {
  // Handle success
  console.log(data.data);
} else {
  // Handle error
  console.error(data.error, data.code);
}
```

---

*Last Updated: January 2024*

