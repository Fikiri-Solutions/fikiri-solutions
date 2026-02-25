# Background Jobs Architecture

**Status**: RQ infrastructure implemented  
**Last Updated**: Feb 2026

---

## Overview

Fikiri Solutions uses Redis Queue (RQ) for background job processing. Long-running tasks (Gmail sync, email processing, AI operations) are moved to background jobs to prevent blocking HTTP request handlers.

---

## Architecture

### Queue Structure

**Queues:**
- `fikiri:email` - Email processing (Gmail sync, email sending)
- `fikiri:ai` - AI/LLM operations (chatbot, email classification)
- `fikiri:crm` - CRM operations (lead updates, contact sync)

**Job Lifecycle:**
1. **Enqueue**: Job added to Redis queue
2. **Dequeue**: Worker picks up job
3. **Process**: Task function executes
4. **Complete/Fail**: Job marked as completed or failed
5. **Retry**: Failed jobs retry up to `max_retries` times

---

## Implementation

### Core Components

**`core/redis_queues.py`**
- `RedisQueue` class - Queue management
- `Job` dataclass - Job structure
- `JobStatus` enum - Job states
- Global queue instances: `email_queue`, `ai_queue`, `crm_queue`

**`routes/jobs.py`**
- `GET /api/jobs/<job_id>` - Get job status
- `GET /api/jobs/queue/<queue_name>/stats` - Queue statistics
- `GET /api/jobs/user/<user_id>/recent` - User's recent jobs

**`scripts/rq_worker.py`**
- Worker script to process jobs
- Registers all task functions
- Handles graceful shutdown

---

## Usage

### Enqueuing Jobs

**Gmail Sync:**
```python
from core.redis_queues import get_email_queue
from email_automation.gmail_sync_jobs import GmailSyncJobManager

sync_job_manager = GmailSyncJobManager()
job_id = sync_job_manager.queue_sync_job(user_id, sync_type='manual')

# Enqueue to RQ
email_queue = get_email_queue()
if email_queue.is_connected():
    email_queue.register_task('process_gmail_sync', sync_job_manager.process_sync_job)
    rq_job_id = email_queue.enqueue_job('process_gmail_sync', {'job_id': job_id}, max_retries=3)
```

**Email Sending:**
```python
from core.redis_queues import send_email_async

job_id = send_email_async(
    to='user@example.com',
    subject='Welcome',
    body='Welcome to Fikiri!'
)
```

**AI Processing:**
```python
from core.redis_queues import process_ai_request_async

job_id = process_ai_request_async(
    prompt='Classify this email',
    user_id=123
)
```

### Checking Job Status

**Via API:**
```bash
GET /api/jobs/<job_id>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "job_id": "abc-123",
    "status": "completed",
    "created_at": 1234567890,
    "completed_at": 1234567900,
    "result": {...}
  }
}
```

**Via Code:**
```python
from core.redis_queues import email_queue

job = email_queue.get_job_status(job_id)
if job:
    print(f"Status: {job.status.value}")
    print(f"Retry count: {job.retry_count}")
```

---

## Running Workers

### Development

```bash
# Process all queues
python scripts/rq_worker.py

# Process specific queue
python scripts/rq_worker.py email
python scripts/rq_worker.py ai
python scripts/rq_worker.py crm
```

### Production

**Using systemd (Linux):**

Create `/etc/systemd/system/fikiri-rq-worker.service`:
```ini
[Unit]
Description=Fikiri RQ Worker
After=network.target redis.service

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/Fikiri
ExecStart=/usr/bin/python3 scripts/rq_worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable fikiri-rq-worker.service
sudo systemctl start fikiri-rq-worker.service
```

**Using Docker Compose:**

```yaml
services:
  rq-worker:
    build: .
    command: python scripts/rq_worker.py
    environment:
      - REDIS_URL=${REDIS_URL}
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - redis
```

**Using Render/Vercel:**

Use platform cron jobs or background workers:
- Render: Background Workers
- Vercel: Serverless Functions (with timeout limits)

---

## Task Registration

All tasks must be registered before workers can process them:

```python
from core.redis_queues import email_queue

@email_queue.task(max_retries=3)
def my_task(arg1: str, arg2: int):
    """My task implementation"""
    # Do work
    return {'success': True, 'result': '...'}
```

Or manually:
```python
email_queue.register_task('my_task', my_task_function)
```

---

## Retry Logic

**Automatic Retries:**
- Jobs retry up to `max_retries` times (default: 3)
- Exponential backoff between retries
- Retry count tracked in job metadata

**Manual Retry:**
```python
queue.fail_job(job_id, error_message, retry=True)
```

---

## Monitoring

### Queue Statistics

```bash
GET /api/jobs/queue/email/stats
```

Response:
```json
{
  "success": true,
  "data": {
    "queue": "email",
    "stats": {
      "pending_jobs": 5,
      "delayed_jobs": 2,
      "total_jobs": 100,
      "total_results": 95
    }
  }
}
```

### Job Status Endpoints

- `GET /api/jobs/<job_id>` - Get job status
- `GET /api/jobs/user/<user_id>/recent` - Recent jobs for user

---

## Migration from Threading

**Before (Threading):**
```python
import threading

def process_in_background():
    result = sync_job_manager.process_sync_job(job_id)

thread = threading.Thread(target=process_in_background, daemon=True)
thread.start()
```

**After (RQ with Fallback):**
```python
from core.redis_queues import get_email_queue

email_queue = get_email_queue()
if email_queue.is_connected():
    # Primary path: Use RQ
    email_queue.register_task('process_gmail_sync', sync_job_manager.process_sync_job)
    rq_job_id = email_queue.enqueue_job('process_gmail_sync', {'job_id': job_id}, max_retries=3)
else:
    # Fallback: Use threading when Redis unavailable
    import threading
    def process_in_background():
        result = sync_job_manager.process_sync_job(job_id)
    thread = threading.Thread(target=process_in_background, daemon=True)
    thread.start()
```

**Note**: Threading fallback is intentional for resilience, but Redis should be available in production.

---

## Best Practices

### 1. Idempotency

All tasks should be idempotent (safe to retry):
```python
def process_email(email_id: str):
    # Check if already processed
    if is_already_processed(email_id):
        return {'status': 'skipped', 'reason': 'already_processed'}
    
    # Process email
    result = process(email_id)
    mark_as_processed(email_id)
    return result
```

### 2. Error Handling

Always handle errors gracefully:
```python
def my_task(data: dict):
    try:
        result = process(data)
        return {'success': True, 'result': result}
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise  # Let RQ handle retry
```

### 3. Timeouts

Set reasonable timeouts for tasks:
- Email sync: 5 minutes
- AI processing: 2 minutes
- CRM updates: 30 seconds

### 4. Job Size

Keep job payloads small:
- ✅ Pass IDs/references, not full objects
- ❌ Don't pass large data structures

---

## Troubleshooting

### Jobs Not Processing

1. **Check Redis connection:**
   ```python
   from core.redis_queues import email_queue
   print(email_queue.is_connected())  # Should be True
   ```

2. **Check worker is running:**
   ```bash
   ps aux | grep rq_worker
   ```

3. **Check queue stats:**
   ```bash
   curl http://localhost:5000/api/jobs/queue/email/stats
   ```

### Jobs Failing

1. **Check job status:**
   ```bash
   curl http://localhost:5000/api/jobs/<job_id>
   ```

2. **Check worker logs:**
   ```bash
   journalctl -u fikiri-rq-worker -f
   ```

3. **Check Redis for job data:**
   ```bash
   redis-cli
   > GET fikiri:job:<job_id>
   ```

---

## Next Steps

1. [x] Move Gmail sync from threading to RQ
2. [x] Add job status endpoints
3. [ ] Move email processing pipeline to RQ
4. [ ] Move heavy AI operations to RQ
5. [ ] Add job retry with exponential backoff (already implemented)
6. [ ] Add job monitoring dashboard
7. [ ] Add job cancellation endpoint

---

*Last updated: Feb 2026*
