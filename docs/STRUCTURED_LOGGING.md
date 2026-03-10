# Structured Logging with Trace IDs

**Status**: Implemented  
**Last Updated**: Feb 2026

---

## Overview

Fikiri Solutions uses structured JSON logging with trace IDs for end-to-end request tracking across all services, background jobs, and async operations.

---

## Trace ID Propagation

### Request Flow

1. **HTTP Request** → Extract `X-Trace-ID` header (or generate new UUID)
2. **Flask Middleware** → Set trace ID in Flask `g` context
3. **API Handler** → Logs include trace_id (if available)
4. **Background Jobs** → Caller must pass trace_id in job args (see Usage)
5. **Worker** → Reads trace_id from job.args and sets in context
6. **Response** → Include trace ID in `X-Trace-ID` response header

**Note**: `redis_queues.py` does not automatically add trace_id to job args. Callers must explicitly pass it (as `routes/business.py` does for Gmail sync).

### Components

**`core/trace_context.py`**
- `get_trace_id()` - Get current trace ID (from Flask `g` or context variable)
- `set_trace_id()` - Set trace ID for current context
- `init_trace_context()` - Flask middleware setup

**`core/structured_logging.py`**
- `StructuredLogger` - JSON logger with trace ID support
- `JSONFormatter` - Formats logs with trace_id, user_id, latency_ms, cost_usd

---

## Usage

### In Flask Routes

Trace ID is automatically set by middleware:

```python
from flask import g
from core.structured_logging import logger

@route('/api/endpoint')
def my_endpoint():
    # Trace ID already set in g.trace_id
    logger.info("Processing request", extra={
        'event': 'request_processed',
        'service': 'api',
        'user_id': get_current_user_id(),
        'latency_ms': 150
    })
    # Logs automatically include trace_id
```

### In Background Jobs

Pass trace ID when enqueueing:

```python
from core.trace_context import get_trace_id
from core.redis_queues import get_email_queue

trace_id = get_trace_id()
email_queue.enqueue_job('my_task', {
    'data': {...},
    'trace_id': trace_id  # Pass trace ID
})
```

In worker, trace ID is set automatically:

```python
def my_task(data: dict, trace_id: str = None):
    # Trace ID already set in context by worker
    logger.info("Processing task", extra={
        'event': 'task_processed',
        'service': 'background_job'
    })
    # Logs automatically include trace_id
```

### In Webhooks

Trace ID extracted from headers:

```python
# In webhook handler
trace_id = request.headers.get('X-Trace-ID') or request.headers.get('X-Request-ID')
set_trace_id(trace_id)

logger.info("Webhook received", extra={
    'event': 'webhook_received',
    'service': 'webhook',
    'webhook_type': 'tally'
})
```

### In Email Pipeline

Pass trace ID explicitly:

```python
from email_automation.pipeline import orchestrate_incoming
from core.trace_context import get_trace_id

trace_id = get_trace_id()
result = orchestrate_incoming(parsed, user_id=user_id, trace_id=trace_id)
```

---

## Log Format

All logs follow this structure:

```json
{
  "timestamp": "2026-02-19T10:30:00.123Z",
  "level": "INFO",
  "message": "Processing request",
  "service": "api",
  "trace_id": "abc-123-def-456",
  "user_id": 123,
  "latency_ms": 150,
  "cost_usd": 0.001,
  "event": "request_processed",
  "severity": "INFO",
  "module": "routes.business",
  "function": "my_endpoint",
  "line": 42
}
```

### Required Fields

- `timestamp` - ISO 8601 timestamp
- `level` - Log level (DEBUG, INFO, WARN, ERROR)
- `message` - Human-readable message
- `service` - Service name (api, email, crm, ai, webhook, background_job)
- `trace_id` - Request trace ID (UUID)

### Optional Fields

- `user_id` - User ID (when available)
- `latency_ms` - Request/operation latency in milliseconds
- `cost_usd` - Cost in USD (for LLM calls)
- `event` - Event type (e.g., "request_processed", "job_completed")
- `severity` - Severity level (matches level)
- `endpoint` - API endpoint
- `method` - HTTP method
- `status_code` - HTTP status code
- `error` - Error message (for errors)

---

## Trace ID Headers

**Request Headers:**
- `X-Trace-ID` - Trace ID header (only header read by middleware)

**Response Headers:**
- `X-Trace-ID` - Echoed trace ID (for client correlation)

---

## Integration Points

### ✅ Implemented

- ✅ Flask request middleware (extracts `X-Trace-ID` header or generates UUID)
- ✅ Structured logging (includes trace_id when available)
- ✅ Webhook processing (Tally, Typeform, Jotform, Generic extract trace ID)
- ✅ Background jobs (callers pass trace_id in job args; worker sets context)
- ✅ Email pipeline (accepts trace_id parameter)
- ✅ Gmail sync jobs (propagates trace ID)

**Note**: 
- Middleware only reads `X-Trace-ID` header (not `X-Request-ID`)
- `redis_queues.py` does not automatically add trace_id; callers must pass it
- JSONFormatter includes trace_id/user_id/latency_ms/cost_usd only if present
- Pre-formatted JSON logs (already JSON strings) are returned unchanged and may not include trace_id

### 🔄 Automatic Propagation

Trace IDs automatically propagate through:
- Flask request → response cycle
- Background job enqueue → worker → completion
- Email pipeline → AI processing → CRM logging

---

## Best Practices

### 1. Always Include Trace ID

```python
# ✅ Good
logger.info("Processing", extra={'trace_id': get_trace_id()})

# ❌ Bad (trace ID missing)
logger.info("Processing")
```

### 2. Pass Trace ID to Background Jobs

```python
# ✅ Good
queue.enqueue_job('task', {'data': data, 'trace_id': get_trace_id()})

# ❌ Bad (trace ID not passed)
queue.enqueue_job('task', {'data': data})
```

### 3. Use Structured Logging

```python
# ✅ Good
logger.info("Request processed", extra={
    'event': 'request_processed',
    'service': 'api',
    'latency_ms': 150,
    'user_id': user_id
})

# ❌ Bad (unstructured)
logger.info(f"Request processed for user {user_id} in {latency_ms}ms")
```

### 4. Include Context in Logs

```python
# ✅ Good
logger.error("Failed to process", extra={
    'event': 'processing_failed',
    'service': 'email',
    'error': str(e),
    'user_id': user_id,
    'email_id': email_id
})

# ❌ Bad (missing context)
logger.error(f"Failed: {e}")
```

---

## Monitoring & Debugging

### Finding Logs by Trace ID

```bash
# Search logs for specific trace ID
grep "abc-123-def-456" logs/app.log

# Or using jq (if logs are JSON)
cat logs/app.log | jq 'select(.trace_id == "abc-123-def-456")'
```

### Log Aggregation

**Recommended Tools:**
- **Datadog** - Log aggregation + APM
- **Logtail** - Simple log aggregation
- **ELK Stack** - Elasticsearch + Logstash + Kibana
- **Grafana Loki** - Log aggregation for Grafana

**Query Example:**
```
trace_id:abc-123-def-456
```

---

## Testing

### Unit Tests

```python
def test_trace_id_propagation():
    from core.trace_context import set_trace_id, get_trace_id
    
    trace_id = "test-trace-123"
    set_trace_id(trace_id)
    
    assert get_trace_id() == trace_id
```

### Integration Tests

```python
def test_api_trace_id():
    response = client.post('/api/endpoint', headers={'X-Trace-ID': 'test-123'})
    
    assert response.headers['X-Trace-ID'] == 'test-123'
    # Check logs contain trace_id
```

---

## Troubleshooting

### Trace ID Not Appearing in Logs

1. **Check middleware initialization:**
   ```python
   # In app.py
   from core.trace_context import init_trace_context
   init_trace_context(app)
   ```

2. **Check structured logging import:**
   ```python
   from core.structured_logging import logger
   # Not: import logging; logger = logging.getLogger(__name__)
   ```

3. **Check trace context availability:**
   ```python
   from core.trace_context import get_trace_id
   trace_id = get_trace_id()
   print(f"Current trace ID: {trace_id}")
   ```

### Trace ID Not Propagating to Background Jobs

1. **Check job args include trace_id:**
   ```python
   queue.enqueue_job('task', {'trace_id': get_trace_id(), ...})
   ```

2. **Check worker sets trace ID:**
   ```python
   # In core/redis_queues.py start_worker()
   set_trace_id(job.args.get('trace_id'))
   ```

---

## Next Steps

- [x] Trace context management
- [x] Flask middleware
- [x] Structured logging integration
- [x] Webhook propagation
- [x] Background job propagation
- [x] Email pipeline propagation
- [ ] Log aggregation setup (Datadog/Logtail)
- [ ] Trace ID dashboard
- [ ] Distributed tracing (OpenTelemetry)

---

*Last updated: Feb 2026*
