# Public API Documentation

## Overview

Fikiri Solutions provides a public API for external clients to integrate chatbot and AI analysis capabilities. The API uses API key authentication, supports CORS, and includes tenant isolation and rate limiting.

## Base URL

```
Production: https://api.fikirisolutions.com/api/public
Development: http://localhost:5000/api/public
```

## Authentication

All endpoints require an API key in the request headers:

```
X-API-Key: fik_your_api_key_here
```

Or using Bearer token format:

```
Authorization: Bearer fik_your_api_key_here
```

### Getting an API Key

API keys are managed through the Fikiri dashboard. Each API key:
- Is associated with a user account
- Can have tenant isolation (optional)
- Has configurable rate limits
- Supports scoped permissions
- Can be revoked at any time

## Rate Limiting

- **Default**: 60 requests per minute, 1000 requests per hour
- **Headers**: Rate limit info is included in response headers:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `X-RateLimit-Reset`: Unix timestamp when limit resets

## CORS

The public API supports CORS for browser-based integrations. All origins are allowed by default (can be restricted per tenant).

---

## Endpoints

### 1. Chatbot Query

Query the chatbot with natural language questions.

**Endpoint:** `POST /chatbot/query`

**Request:**
```json
{
  "query": "What are your business hours?",
  "conversation_id": "optional-conversation-id",
  "context": {
    "user_id": "optional-user-id",
    "session_id": "optional-session-id"
  }
}
```

**Response:**
```json
{
  "success": true,
  "query": "What are your business hours?",
  "response": "We're open Monday-Friday 9am-5pm EST.",
  "sources": [
    {
      "type": "faq",
      "id": 123,
      "question": "What are your business hours?",
      "answer": "We're open Monday-Friday 9am-5pm EST.",
      "confidence": 0.95
    }
  ],
  "confidence": 0.95,
  "conversation_id": "conv_abc123",
  "tenant_id": "tenant_xyz"
}
```

**Example (cURL):**
```bash
curl -X POST https://api.fikirisolutions.com/api/public/chatbot/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: fik_your_api_key_here" \
  -d '{
    "query": "What are your business hours?"
  }'
```

**Example (JavaScript):**
```javascript
const response = await fetch('https://api.fikirisolutions.com/api/public/chatbot/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'fik_your_api_key_here'
  },
  body: JSON.stringify({
    query: 'What are your business hours?'
  })
});

const data = await response.json();
console.log(data.response);
```

---

### 2. Contact Analysis

Analyze a contact using AI to get insights, scoring, and recommendations.

**Endpoint:** `POST /ai/analyze/contact`

**Request:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "company": "Acme Corp",
  "phone": "+1234567890",
  "job_title": "CEO",
  "notes": "Interested in our product"
}
```

**Response:**
```json
{
  "success": true,
  "analysis": {
    "contact_score": 85,
    "engagement_level": "high",
    "recommended_actions": [
      "Schedule a demo call",
      "Send product documentation",
      "Follow up within 24 hours"
    ],
    "insights": [
      "High-value contact based on job title",
      "Company matches target profile",
      "Shows strong interest signals"
    ],
    "risk_factors": [],
    "opportunities": [
      "Potential enterprise deal",
      "Decision maker identified"
    ]
  },
  "metadata": {
    "analyzed_at": "2024-01-01T12:00:00Z",
    "model_version": "gpt-4"
  }
}
```

**Example:**
```bash
curl -X POST https://api.fikirisolutions.com/api/public/ai/analyze/contact \
  -H "Content-Type: application/json" \
  -H "X-API-Key: fik_your_api_key_here" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "company": "Acme Corp"
  }'
```

---

### 3. Lead Analysis

Analyze a lead to determine conversion probability, priority, and next steps.

**Endpoint:** `POST /ai/analyze/lead`

**Request:**
```json
{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "company": "Tech Corp",
  "source": "website",
  "status": "new",
  "notes": "Requested demo"
}
```

**Response:**
```json
{
  "success": true,
  "analysis": {
    "lead_score": 75,
    "conversion_probability": 0.75,
    "priority": "high",
    "recommended_actions": [
      "Qualify lead with discovery questions",
      "Send personalized demo invitation",
      "Assign to sales team"
    ],
    "insights": [
      "Strong intent signals from website source",
      "Company size indicates good fit",
      "Demo request shows high engagement"
    ],
    "next_steps": [
      "Schedule discovery call",
      "Prepare custom demo",
      "Research company background"
    ],
    "estimated_value": 50000
  },
  "metadata": {
    "analyzed_at": "2024-01-01T12:00:00Z",
    "model_version": "gpt-4"
  }
}
```

---

### 4. Business Summary

Get AI-powered business analysis and market insights.

**Endpoint:** `POST /ai/analyze/business`

**Request:**
```json
{
  "business_name": "Acme Corporation",
  "industry": "Technology",
  "description": "SaaS platform for business automation",
  "website": "https://acme.com",
  "employee_count": 100,
  "revenue_range": "$10M-$50M",
  "location": "San Francisco, CA"
}
```

**Response:**
```json
{
  "success": true,
  "summary": {
    "business_name": "Acme Corporation",
    "industry": "Technology",
    "size_category": "medium",
    "key_insights": [
      "Growing SaaS company in competitive market",
      "Strong revenue indicates product-market fit",
      "Mid-size suggests scaling phase"
    ],
    "market_position": "Established player with growth potential",
    "growth_potential": "high",
    "recommendations": [
      "Focus on customer retention strategies",
      "Explore expansion opportunities",
      "Consider strategic partnerships"
    ]
  },
  "metadata": {
    "analyzed_at": "2024-01-01T12:00:00Z",
    "model_version": "gpt-4"
  }
}
```

---

### 5. Health Check

Check API health status (no authentication required).

**Endpoint:** `GET /chatbot/health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "service": "public-chatbot-api"
}
```

---

## Error Responses

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error message",
  "error_code": "ERROR_CODE"
}
```

### Common Error Codes

- `MISSING_API_KEY` (401): API key not provided
- `INVALID_API_KEY` (401): API key is invalid or expired
- `INSUFFICIENT_SCOPE` (403): API key lacks required permissions
- `RATE_LIMIT_EXCEEDED` (429): Rate limit exceeded
- `MISSING_QUERY` (400): Required field missing
- `VALIDATION_ERROR` (400): Request validation failed
- `AI_SERVICE_UNAVAILABLE` (503): AI service temporarily unavailable
- `INTERNAL_ERROR` (500): Internal server error

---

## Embedding the Chatbot

### HTML Widget

```html
<!DOCTYPE html>
<html>
<head>
  <title>Chatbot Widget</title>
</head>
<body>
  <div id="chatbot-widget"></div>
  
  <script>
    const API_KEY = 'fik_your_api_key_here';
    const API_URL = 'https://api.fikirisolutions.com/api/public/chatbot/query';
    
    async function sendMessage(query) {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': API_KEY
        },
        body: JSON.stringify({ query })
      });
      
      const data = await response.json();
      return data.response;
    }
    
    // Example usage
    sendMessage('What are your business hours?')
      .then(response => console.log(response));
  </script>
</body>
</html>
```

### React Component

```jsx
import React, { useState } from 'react';

function ChatbotWidget({ apiKey }) {
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const res = await fetch('https://api.fikirisolutions.com/api/public/chatbot/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify({ query })
      });
      
      const data = await res.json();
      setResponse(data.response);
    } catch (error) {
      console.error('Chatbot error:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div>
      <form onSubmit={handleSubmit}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question..."
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Sending...' : 'Send'}
        </button>
      </form>
      {response && <div>{response}</div>}
    </div>
  );
}

export default ChatbotWidget;
```

---

## Best Practices

1. **Store API keys securely**: Never expose API keys in client-side code. Use environment variables or secure storage.

2. **Handle rate limits**: Implement exponential backoff when rate limits are exceeded.

3. **Use conversation IDs**: Maintain conversation context by passing `conversation_id` in requests.

4. **Error handling**: Always check `success` field and handle errors appropriately.

5. **Caching**: Cache responses when appropriate to reduce API calls.

6. **Monitoring**: Monitor API usage and set up alerts for failures.

---

## Support

For API support, contact:
- Email: api@fikirisolutions.com
- Documentation: https://docs.fikirisolutions.com
- Status Page: https://status.fikirisolutions.com
