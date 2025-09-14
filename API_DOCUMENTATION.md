# Fikiri Solutions - API Documentation

## 🔗 Base URL
```
Production: https://api.fikirisolutions.com
Development: http://localhost:8000
```

## 🔐 Authentication

### API Key Authentication
```bash
curl -H "X-API-Key: your_api_key" https://api.fikirisolutions.com/endpoint
```

### JWT Token Authentication
```bash
# Login first
curl -X POST https://api.fikirisolutions.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use token in subsequent requests
curl -H "Authorization: Bearer your_jwt_token" https://api.fikirisolutions.com/endpoint
```

## 📧 Email Management

### Process Emails
```bash
POST /email/process
Content-Type: application/json

{
  "query": "is:unread",
  "max_results": 10,
  "actions": ["read", "archive"]
}
```

### Send Reply
```bash
POST /email/reply
Content-Type: application/json

{
  "message_id": "message_id_here",
  "template": "general_response",
  "custom_message": "Optional custom message"
}
```

## 🎯 CRM Operations

### List Leads
```bash
GET /crm/leads?stage=new&limit=50&offset=0
```

### Create Lead
```bash
POST /crm/leads
Content-Type: application/json

{
  "email": "lead@example.com",
  "name": "John Doe",
  "source": "website",
  "score": 85,
  "stage": "new"
}
```

### Update Lead
```bash
PUT /crm/leads/{lead_id}
Content-Type: application/json

{
  "stage": "contacted",
  "score": 90,
  "notes": "Initial contact made"
}
```

### CRM Analytics
```bash
GET /crm/analytics?period=30d
```

## 🤖 Chatbot Services

### Basic Chatbot (Tier 1)
```bash
POST /chatbot/basic/chat
Content-Type: application/json

{
  "message": "What are your business hours?",
  "session_id": "optional_session_id"
}
```

### Professional Chatbot (Tier 2)
```bash
POST /chatbot/professional/chat
Content-Type: application/json

{
  "message": "I need help with my account",
  "session_id": "session_123",
  "context": {
    "user_type": "premium",
    "previous_issues": ["billing", "support"]
  }
}
```

### Enterprise Chatbot (Tier 3)
```bash
POST /chatbot/enterprise/chat
Content-Type: application/json

{
  "message": "Analyze my business metrics",
  "session_id": "session_123",
  "business_context": {
    "industry": "technology",
    "company_size": "enterprise",
    "custom_models": ["sentiment", "intent"]
  }
}
```

### Chatbot Learning
```bash
POST /chatbot/learn
Content-Type: application/json

{
  "message": "User question",
  "response": "Bot response",
  "feedback": "positive|negative|neutral",
  "tier": "professional"
}
```

## 🎨 AI Creative Services

### Generate Content
```bash
POST /ai-creative/generate
Content-Type: application/json

{
  "content_type": "email_template",
  "business_context": {
    "industry": "technology",
    "tone": "professional",
    "target_audience": "enterprise"
  },
  "requirements": {
    "length": "medium",
    "include_cta": true,
    "personalization": true
  }
}
```

### Content Analysis
```bash
POST /ai-creative/analyze
Content-Type: application/json

{
  "content": "Your content here",
  "analysis_type": "sentiment|readability|engagement"
}
```

### Model Training
```bash
POST /ai-creative/train
Content-Type: application/json

{
  "model_type": "sentiment",
  "training_data": [
    {"text": "Great service!", "label": "positive"},
    {"text": "Terrible experience", "label": "negative"}
  ],
  "business_profile": "technology_company"
}
```

## 🔄 Workflow Automation

### Trigger Workflow
```bash
POST /workflow/trigger
Content-Type: application/json

{
  "workflow_type": "email_processing",
  "parameters": {
    "query": "is:unread label:leads",
    "action": "auto_reply"
  }
}
```

### Schedule Task
```bash
POST /workflow/schedule
Content-Type: application/json

{
  "task_name": "daily_email_processing",
  "schedule": "0 9 * * *",  # Cron format
  "parameters": {
    "query": "is:unread",
    "max_results": 100
  }
}
```

### Workflow Status
```bash
GET /workflow/status/{task_id}
```

## 🔗 Webhook Integrations

### Tally Form Webhook
```bash
POST /webhook/tally
Content-Type: application/json

{
  "eventId": "event_123",
  "eventType": "FORM_RESPONSE",
  "data": {
    "responseId": "response_123",
    "submissionId": "submission_123",
    "respondentId": "respondent_123",
    "formId": "form_123",
    "formName": "Contact Form",
    "createdAt": "2024-01-01T00:00:00.000Z",
    "fields": [
      {
        "key": "email",
        "label": "Email",
        "type": "EMAIL",
        "value": "user@example.com"
      }
    ]
  }
}
```

### Typeform Webhook
```bash
POST /webhook/typeform
Content-Type: application/json

{
  "event_id": "event_123",
  "event_type": "form_response",
  "form_response": {
    "form_id": "form_123",
    "token": "token_123",
    "submitted_at": "2024-01-01T00:00:00.000Z",
    "answers": [
      {
        "field": {
          "id": "field_123",
          "type": "email",
          "ref": "email_field"
        },
        "email": "user@example.com"
      }
    ]
  }
}
```

### Calendly Webhook
```bash
POST /webhook/calendly
Content-Type: application/json

{
  "event": "invitee.created",
  "time": "2024-01-01T00:00:00.000Z",
  "payload": {
    "event_type": {
      "uuid": "event_type_123",
      "name": "Consultation Call"
    },
    "event": {
      "uuid": "event_123",
      "start_time": "2024-01-01T10:00:00.000Z",
      "end_time": "2024-01-01T11:00:00.000Z"
    },
    "invitee": {
      "uuid": "invitee_123",
      "email": "user@example.com",
      "name": "John Doe"
    }
  }
}
```

## 💳 Stripe Integration

### Create Customer
```bash
POST /stripe/customers
Content-Type: application/json

{
  "email": "customer@example.com",
  "name": "John Doe",
  "metadata": {
    "lead_id": "lead_123",
    "source": "website"
  }
}
```

### Create Subscription
```bash
POST /stripe/subscriptions
Content-Type: application/json

{
  "customer_id": "cus_123",
  "price_id": "price_123",
  "trial_period_days": 14
}
```

### Update Subscription
```bash
PUT /stripe/subscriptions/{subscription_id}
Content-Type: application/json

{
  "price_id": "new_price_123",
  "proration_behavior": "create_prorations"
}
```

## 🗄️ Vector Database

### Store Chat Memory
```bash
POST /vector-db/store
Content-Type: application/json

{
  "session_id": "session_123",
  "message": "User question",
  "response": "Bot response",
  "metadata": {
    "timestamp": "2024-01-01T00:00:00.000Z",
    "user_id": "user_123"
  }
}
```

### Retrieve Similar Context
```bash
GET /vector-db/search?query=user_question&session_id=session_123&limit=5
```

### Update Memory
```bash
PUT /vector-db/memory/{memory_id}
Content-Type: application/json

{
  "message": "Updated message",
  "response": "Updated response",
  "metadata": {
    "updated_at": "2024-01-01T00:00:00.000Z"
  }
}
```

## 🤗 Hugging Face Integration

### Create Dataset
```bash
POST /huggingface/datasets
Content-Type: application/json

{
  "name": "fikiri_chatbot_data",
  "description": "Chatbot training data",
  "data": [
    {"text": "Hello", "label": "greeting"},
    {"text": "Goodbye", "label": "farewell"}
  ]
}
```

### Start Training Job
```bash
POST /huggingface/train
Content-Type: application/json

{
  "dataset_id": "dataset_123",
  "model_name": "distilbert-base-uncased",
  "task": "text-classification",
  "hyperparameters": {
    "learning_rate": 0.0001,
    "batch_size": 16,
    "epochs": 3
  }
}
```

### Get Predictions
```bash
POST /huggingface/predict
Content-Type: application/json

{
  "model_id": "model_123",
  "text": "Input text for prediction"
}
```

## 📊 System Health & Monitoring

### Health Check
```bash
GET /system/health-extended
```

### System Status
```bash
GET /system/status
```

### Performance Metrics
```bash
GET /system/metrics
```

### Service Status
```bash
GET /system/services
```

## ⚡ Rate Limiting

### Limits by Endpoint
- **API Routes**: 10 requests/second
- **Chatbot**: 5 requests/second  
- **Webhooks**: 50 requests/second
- **Auth**: 5 requests/second

### Rate Limit Headers
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 9
X-RateLimit-Reset: 1640995200
```

## 🚨 Error Responses

### Standard Error Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "email",
      "issue": "Invalid email format"
    },
    "timestamp": "2024-01-01T00:00:00.000Z",
    "request_id": "req_123"
  }
}
```

### Common Error Codes
- `VALIDATION_ERROR`: Invalid input data
- `AUTHENTICATION_ERROR`: Invalid credentials
- `AUTHORIZATION_ERROR`: Insufficient permissions
- `RATE_LIMIT_ERROR`: Too many requests
- `SERVICE_ERROR`: Internal service error
- `NOT_FOUND`: Resource not found

## 📝 Response Examples

### Success Response
```json
{
  "success": true,
  "data": {
    "id": "resource_123",
    "status": "created",
    "timestamp": "2024-01-01T00:00:00.000Z"
  },
  "meta": {
    "request_id": "req_123",
    "processing_time": "0.150s"
  }
}
```

### Paginated Response
```json
{
  "success": true,
  "data": [
    {"id": "item_1", "name": "Item 1"},
    {"id": "item_2", "name": "Item 2"}
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 150,
    "pages": 3
  },
  "meta": {
    "request_id": "req_123"
  }
}
```




