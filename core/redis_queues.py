#!/usr/bin/env python3
"""
Redis Queues for Background Jobs - Fikiri Solutions
Async task processing with Redis as message broker
"""

import json
import time
import uuid
import logging
import random
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass

# Import trace context for background jobs
try:
    from core.trace_context import set_trace_id, get_trace_id
    TRACE_CONTEXT_AVAILABLE = True
except ImportError:
    TRACE_CONTEXT_AVAILABLE = False

# Optional Redis integration
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

try:
    from core.config import get_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    get_config = None

logger = logging.getLogger(__name__)

# One process-wide warning instead of N lines when multiple queues init without Redis.
_missing_redis_queue_client_logged = False


class JobStatus(Enum):
    """Job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD = "dead"

@dataclass
class Job:
    """Job data structure"""
    id: str
    task: str
    args: Dict[str, Any]
    status: JobStatus
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    retry_after: Optional[float] = None
    dead_letter: bool = False

def _is_brpop_idle_timeout(exc: BaseException) -> bool:
    """True when BRPOP finished with no job (socket/read timeout), not a real failure."""
    if not REDIS_AVAILABLE or redis is None:
        return False
    if isinstance(exc, redis.TimeoutError):
        return True
    msg = str(exc).lower()
    return "timeout reading from socket" in msg


def _log_queue_idle_wait(queue_name: str, brpop_timeout_s: int = 0) -> None:
    """Structured log for idle worker poll — not a job failure."""
    logger.info(
        "Queue wait timed out (no job); worker continuing",
        extra={
            "event": "queue_idle_wait",
            "service": "background_job",
            "severity": "INFO",
            "metadata": {
                "queue_name": queue_name,
                "brpop_timeout_s": brpop_timeout_s,
            },
        },
    )


def _log_dequeue_reconnect(queue_name: str, error: str) -> None:
    """Structured log when dequeue loses Redis and will reconnect."""
    logger.warning(
        "Redis connection lost during dequeue; reconnecting",
        extra={
            "event": "redis_dequeue_reconnect",
            "service": "background_job",
            "severity": "WARN",
            "metadata": {"queue_name": queue_name, "error": error},
        },
    )


class RedisQueue:
    """Redis-based job queue system"""
    
    def __init__(self, queue_name: str = "fikiri:jobs"):
        self.config = get_config()
        self.redis_client = None
        self._blocking_redis_client = None
        self.queue_name = queue_name
        self.job_prefix = f"fikiri:job:"
        self.result_prefix = f"fikiri:result:"
        self._connect()
        self._registered_tasks = {}
    
    def _connect(self):
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using in-memory queues")
            self.redis_client = None
            return
            
        try:
            from core.redis_connection_helper import get_redis_client
            redis_db = getattr(self.config, 'redis_db', 0) if hasattr(self.config, 'redis_db') else 0
            self.redis_client = get_redis_client(decode_responses=True, db=redis_db)
            if self.redis_client:
                self.redis_client.ping()
                logger.info("✅ Redis queue '%s' connected", self.queue_name)
            else:
                global _missing_redis_queue_client_logged
                if not _missing_redis_queue_client_logged:
                    _missing_redis_queue_client_logged = True
                    logger.warning(
                        "⚠️ Redis job queues have no backing client (Redis unavailable; "
                        "named queues include %s — ops will fail or use fallbacks)",
                        self.queue_name,
                    )
                else:
                    logger.debug("Redis queue '%s' has no client", self.queue_name)
        except Exception as e:
            logger.error(f"❌ Redis queue connection failed: {e}")
            self.redis_client = None

    def _redis_db(self) -> int:
        if hasattr(self.config, "redis_db"):
            return getattr(self.config, "redis_db", 0) or 0
        return 0

    def _get_blocking_redis_client(self):
        """Redis client without socket read timeout — required for BRPOP idle polls."""
        if not REDIS_AVAILABLE:
            return None
        if self._blocking_redis_client is not None:
            try:
                self._blocking_redis_client.ping()
                return self._blocking_redis_client
            except Exception:
                self._blocking_redis_client = None
        try:
            from core.redis_connection_helper import get_redis_client
            client = get_redis_client(
                decode_responses=True,
                db=self._redis_db(),
                socket_timeout=None,
            )
            if client:
                self._blocking_redis_client = client
            return client
        except Exception as e:
            logger.debug("Blocking Redis client unavailable: %s", e)
            return None

    def _invalidate_redis_clients(self) -> None:
        self.redis_client = None
        self._blocking_redis_client = None

    def _reconnect_redis_clients(self) -> None:
        """Drop stale clients and re-establish queue connections."""
        self._invalidate_redis_clients()
        self._connect()
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except Exception as ping_error:
            logger.debug("Redis queue ping failed: %s", ping_error)
            return False
    
    def register_task(self, task_name: str, task_func: Callable):
        """Register a task function"""
        self._registered_tasks[task_name] = task_func
        logger.info(f"✅ Registered task: {task_name}")
    
    def enqueue_job(self, task: str, args: Dict[str, Any] = None, 
                   max_retries: int = 3, delay: int = 0) -> str:
        """Enqueue a new job"""
        if not self.is_connected():
            raise Exception("Redis queue not connected")
        
        try:
            job_id = str(uuid.uuid4())
            args = args or {}
            
            job = Job(
                id=job_id,
                task=task,
                args=args,
                status=JobStatus.PENDING,
                created_at=time.time(),
                max_retries=max_retries
            )
            
            # Store job data
            job_key = f"{self.job_prefix}{job_id}"
            self.redis_client.setex(
                job_key, 
                86400,  # 24 hours TTL
                json.dumps(job.__dict__, default=str)
            )
            
            # Add to queue
            if delay > 0:
                # Delayed job
                self.redis_client.zadd(
                    f"{self.queue_name}:delayed",
                    {job_id: time.time() + delay}
                )
            else:
                # Immediate job
                self.redis_client.lpush(f"{self.queue_name}:pending", job_id)
            
            logger.info(f"✅ Enqueued job {job_id}: {task}")
            return job_id
            
        except Exception as e:
            logger.error(f"❌ Job enqueue failed: {e}")
            raise
    
    def dequeue_job(self, timeout: int = 0) -> Optional[Job]:
        """Dequeue next job"""
        if not self.is_connected():
            return None
        
        try:
            # Check for delayed jobs first
            now = time.time()
            delayed_jobs = self.redis_client.zrangebyscore(
                f"{self.queue_name}:delayed",
                0, now
            )
            
            if delayed_jobs:
                # Move delayed jobs to pending queue
                for job_id in delayed_jobs:
                    self.redis_client.lpush(f"{self.queue_name}:pending", job_id)
                    self.redis_client.zrem(f"{self.queue_name}:delayed", job_id)
            
            # Get next pending job (blocking client avoids socket_timeout vs BRPOP race)
            if timeout > 0:
                blocking = self._get_blocking_redis_client()
                if not blocking:
                    return None
                try:
                    result = blocking.brpop(f"{self.queue_name}:pending", timeout)
                except Exception as brpop_error:
                    if _is_brpop_idle_timeout(brpop_error):
                        _log_queue_idle_wait(self.queue_name, brpop_timeout_s=timeout)
                        return None
                    raise
                if result:
                    job_id = result[1]
                else:
                    return None
            else:
                job_id = self.redis_client.rpop(f"{self.queue_name}:pending")
                if not job_id:
                    return None
            
            # Get job data
            job_key = f"{self.job_prefix}{job_id}"
            job_data = self.redis_client.get(job_key)
            
            if job_data:
                job_dict = json.loads(job_data)
                job = Job(**job_dict)
                
                # Update job status
                job.status = JobStatus.PROCESSING
                job.started_at = time.time()
                
                self.redis_client.setex(
                    job_key,
                    86400,
                    json.dumps(job.__dict__, default=str)
                )
                
                logger.info(f"✅ Dequeued job {job_id}: {job.task}")
                return job
            
            return None
            
        except Exception as e:
            if _is_brpop_idle_timeout(e):
                _log_queue_idle_wait(self.queue_name, brpop_timeout_s=timeout)
                return None
            if REDIS_AVAILABLE and redis is not None and isinstance(
                e, (redis.ConnectionError, OSError)
            ):
                _log_dequeue_reconnect(self.queue_name, str(e))
                self._reconnect_redis_clients()
                return None
            logger.error(
                "Job dequeue failed",
                extra={
                    "event": "job_dequeue_failed",
                    "service": "background_job",
                    "severity": "ERROR",
                    "metadata": {"queue_name": self.queue_name, "error": str(e)},
                },
            )
            return None
    
    def complete_job(self, job_id: str, result: Any = None):
        """Mark job as completed"""
        if not self.is_connected():
            return False
        
        try:
            job_key = f"{self.job_prefix}{job_id}"
            job_data = self.redis_client.get(job_key)
            
            if job_data:
                job_dict = json.loads(job_data)
                job = Job(**job_dict)
                
                job.status = JobStatus.COMPLETED
                job.completed_at = time.time()
                job.result = result
                
                # Update job data
                self.redis_client.setex(
                    job_key,
                    86400,
                    json.dumps(job.__dict__, default=str)
                )
                
                # Store result
                result_key = f"{self.result_prefix}{job_id}"
                self.redis_client.setex(
                    result_key,
                    86400,
                    json.dumps(result, default=str)
                )
                
                logger.info(f"✅ Completed job {job_id}")
                if job.retry_count > 0:
                    logger.info(
                        "Queue job completed after retry",
                        extra={
                            "event": "job.completed_after_retry",
                            "service": "background_job",
                            "severity": "INFO",
                            "job_id": job_id,
                            "task": job.task,
                            "queue_name": self.queue_name,
                            "retry_count": job.retry_count,
                        },
                    )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Job completion failed: {e}")
            return False
    
    def _retry_delay_seconds(self, retry_count: int) -> int:
        """Return bounded exponential retry delay with small jitter.

        retry_count is 1-based for the failure that just happened. The base
        schedule is approximately 30s, 2m, 10m, then capped.
        """
        base_delays = (30, 120, 600)
        base = base_delays[min(max(retry_count, 1), len(base_delays)) - 1]
        jitter = random.randint(0, max(1, int(base * 0.1)))
        return base + jitter

    def fail_job(self, job_id: str, error: str, retry: bool = True):
        """Mark job as failed, scheduling delayed retries before dead-letter."""
        if not self.is_connected():
            return False
        
        try:
            job_key = f"{self.job_prefix}{job_id}"
            job_data = self.redis_client.get(job_key)
            
            if job_data:
                job_dict = json.loads(job_data)
                job = Job(**job_dict)
                
                job.error = error
                job.retry_count += 1
                now = time.time()
                will_retry = retry and job.retry_count <= job.max_retries
                
                if will_retry:
                    job.status = JobStatus.RETRYING
                    delay = self._retry_delay_seconds(job.retry_count)
                    job.retry_after = now + delay
                    job.dead_letter = False
                    self.redis_client.zadd(
                        f"{self.queue_name}:delayed",
                        {job_id: job.retry_after},
                    )
                    logger.warning(
                        "Queue job retry scheduled",
                        extra={
                            "event": "job.retry_scheduled",
                            "service": "background_job",
                            "severity": "WARN",
                            "job_id": job_id,
                            "task": job.task,
                            "queue_name": self.queue_name,
                            "retry_count": job.retry_count,
                            "max_retries": job.max_retries,
                            "retry_delay_seconds": delay,
                            "retry_after": job.retry_after,
                        },
                    )
                else:
                    job.status = JobStatus.DEAD if retry else JobStatus.FAILED
                    job.completed_at = now
                    job.retry_after = None
                    job.dead_letter = bool(retry)
                    logger.error(
                        "Queue job terminal failure",
                        extra={
                            "event": "job.dead_letter" if job.dead_letter else "job.retry_skipped",
                            "service": "background_job",
                            "severity": "ERROR",
                            "job_id": job_id,
                            "task": job.task,
                            "queue_name": self.queue_name,
                            "retry_count": job.retry_count,
                            "max_retries": job.max_retries,
                            "dead_letter": job.dead_letter,
                            "error": error,
                        },
                    )
                
                # Update job data
                self.redis_client.setex(
                    job_key,
                    86400,
                    json.dumps(job.__dict__, default=str)
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Job failure handling failed: {e}")
            return False
    
    def get_job_status(self, job_id: str) -> Optional[Job]:
        """Get job status"""
        if not self.is_connected():
            return None
        
        try:
            job_key = f"{self.job_prefix}{job_id}"
            job_data = self.redis_client.get(job_key)
            
            if job_data:
                job_dict = json.loads(job_data)
                return Job(**job_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Job status retrieval failed: {e}")
            return None
    
    def get_job_result(self, job_id: str) -> Optional[Any]:
        """Get job result"""
        if not self.is_connected():
            return None
        
        try:
            result_key = f"{self.result_prefix}{job_id}"
            result_data = self.redis_client.get(result_key)
            
            if result_data:
                return json.loads(result_data)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Job result retrieval failed: {e}")
            return None
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        if not self.is_connected():
            return {}
        
        try:
            stats = {
                'pending_jobs': self.redis_client.llen(f"{self.queue_name}:pending"),
                'delayed_jobs': self.redis_client.zcard(f"{self.queue_name}:delayed"),
                'total_jobs': len(self.redis_client.keys(f"{self.job_prefix}*")),
                'total_results': len(self.redis_client.keys(f"{self.result_prefix}*"))
            }
            
            logger.info(f"✅ Queue stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Queue stats failed: {e}")
            return {}
    
    def clear_queue(self, queue_type: str = "all") -> bool:
        """Clear queue"""
        if not self.is_connected():
            return False
        
        try:
            if queue_type in ["all", "pending"]:
                self.redis_client.delete(f"{self.queue_name}:pending")
            
            if queue_type in ["all", "delayed"]:
                self.redis_client.delete(f"{self.queue_name}:delayed")
            
            if queue_type in ["all", "jobs"]:
                job_keys = self.redis_client.keys(f"{self.job_prefix}*")
                if job_keys:
                    self.redis_client.delete(*job_keys)
            
            if queue_type in ["all", "results"]:
                result_keys = self.redis_client.keys(f"{self.result_prefix}*")
                if result_keys:
                    self.redis_client.delete(*result_keys)
            
            logger.info(f"✅ Cleared queue: {queue_type}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Queue clear failed: {e}")
            return False

# Global queue instances
email_queue = RedisQueue("fikiri:email")
ai_queue = RedisQueue("fikiri:ai")
crm_queue = RedisQueue("fikiri:crm")
webhook_queue = RedisQueue("fikiri:webhook")
automation_queue = RedisQueue("fikiri:automation")

def get_email_queue() -> RedisQueue:
    """Get email processing queue"""
    return email_queue

def get_ai_queue() -> RedisQueue:
    """Get AI processing queue"""
    return ai_queue

def get_crm_queue() -> RedisQueue:
    """Get CRM processing queue"""
    return crm_queue

def get_automation_queue() -> RedisQueue:
    """Get automation execution queue"""
    return automation_queue

def get_redis_queue() -> RedisQueue:
    """Get default Redis queue instance"""
    return email_queue

# Task decorators
def task(queue: RedisQueue, max_retries: int = 3):
    """Decorator to register a task"""
    def decorator(func):
        queue.register_task(func.__name__, func)
        return func
    return decorator

# Background job functions
def send_email_async(to: str, subject: str, body: str, **kwargs) -> str:
    """Send email asynchronously"""
    return email_queue.enqueue_job(
        "send_email",
        {
            "to": to,
            "subject": subject,
            "body": body,
            **kwargs
        }
    )

def process_ai_request_async(prompt: str, user_id: str, **kwargs) -> str:
    """Process AI request asynchronously"""
    return ai_queue.enqueue_job(
        "process_ai_request",
        {
            "prompt": prompt,
            "user_id": user_id,
            **kwargs
        }
    )

def update_crm_async(lead_data: Dict[str, Any], **kwargs) -> str:
    """Update CRM asynchronously"""
    return crm_queue.enqueue_job(
        "update_crm",
        {
            "lead_data": lead_data,
            **kwargs
        }
    )

def process_webhook_async(webhook_data: Dict[str, Any], **kwargs) -> str:
    """Process webhook asynchronously"""
    return webhook_queue.enqueue_job(
        "process_webhook",
        {
            "webhook_data": webhook_data,
            **kwargs
        }
    )

# Worker functions
def start_worker(queue: RedisQueue, worker_name: str = "worker"):
    """Start a worker to process jobs"""
    logger.info(f"🚀 Starting {worker_name} for queue {queue.queue_name}")
    
    # Import trace context for background jobs
    try:
        from core.trace_context import set_trace_id, get_trace_id
        TRACE_CONTEXT_AVAILABLE = True
    except ImportError:
        TRACE_CONTEXT_AVAILABLE = False
    
    while True:
        try:
            job = queue.dequeue_job(timeout=5)
            if job:
                # Set trace ID from job args or generate new one
                job_trace_id = job.args.get('trace_id') or str(uuid.uuid4())
                if TRACE_CONTEXT_AVAILABLE:
                    set_trace_id(job_trace_id)
                
                logger.info(f"📋 Processing job {job.id}: {job.task}", extra={
                    'event': 'job_started',
                    'service': 'background_job',
                    'severity': 'INFO',
                    'trace_id': job_trace_id,
                    'job_id': job.id,
                    'task': job.task
                })
                
                # Get task function
                task_func = queue._registered_tasks.get(job.task)
                if task_func:
                    try:
                        result = task_func(**job.args)
                        queue.complete_job(job.id, result)
                        logger.info(f"✅ Completed job {job.id}", extra={
                            'event': 'job_completed',
                            'service': 'background_job',
                            'severity': 'INFO',
                            'trace_id': job_trace_id,
                            'job_id': job.id,
                            'task': job.task
                        })
                    except Exception as e:
                        queue.fail_job(job.id, str(e))
                        logger.error(f"❌ Failed job {job.id}: {e}", extra={
                            'event': 'job_failed',
                            'service': 'background_job',
                            'severity': 'ERROR',
                            'trace_id': job_trace_id,
                            'job_id': job.id,
                            'task': job.task,
                            'error': str(e)
                        })
                else:
                    queue.fail_job(job.id, f"Unknown task: {job.task}")
                    logger.error(f"❌ Unknown task: {job.task}", extra={
                        'event': 'job_failed',
                        'service': 'background_job',
                        'severity': 'ERROR',
                        'trace_id': job_trace_id,
                        'job_id': job.id,
                        'task': job.task,
                        'error': 'Unknown task'
                    })
            else:
                # No jobs available, sleep briefly
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info(f"🛑 Stopping {worker_name}")
            break
        except Exception as e:
            logger.error(f"❌ Worker error: {e}")
            time.sleep(5)

# Example task implementations
@task(email_queue)
def send_email(to: str, subject: str, body: str, **kwargs):
    """Send email task implementation"""
    # Import your email service here
    from email_automation.actions import MinimalEmailActions
    
    email_service = MinimalEmailActions()
    result = email_service.send_email(to, subject, body)
    
    return {
        "success": True,
        "message_id": result.get("message_id"),
        "sent_to": to
    }

@task(ai_queue)
def process_ai_request(prompt: str, user_id: str, **kwargs):
    """Process AI request task implementation"""
    # Import your AI service here
    from email_automation.ai_assistant import MinimalAIEmailAssistant as MinimalAIAssistant
    
    ai_service = MinimalAIAssistant()
    result = ai_service.process_request(prompt, user_id)
    
    return {
        "success": True,
        "response": result,
        "user_id": user_id
    }

@task(crm_queue)
def update_crm(lead_data: Dict[str, Any] = None, **kwargs):
    """Update CRM task implementation"""
    # Import your CRM service here
    from crm.service import enhanced_crm_service

    lead_data = lead_data or {}
    raw_uid = lead_data.get("user_id")
    if raw_uid is None:
        logger.error("update_crm job rejected: lead_data missing user_id")
        return {"success": False, "error": "lead_data must include user_id"}
    try:
        user_id = int(raw_uid)
    except (TypeError, ValueError):
        logger.error("update_crm job rejected: invalid user_id %r", raw_uid)
        return {"success": False, "error": "invalid user_id"}
    if user_id <= 0:
        return {"success": False, "error": "invalid user_id"}

    result = enhanced_crm_service.create_lead(user_id, lead_data)
    
    return {
        "success": True,
        "lead_id": result.get("lead_id"),
        "lead_data": lead_data
    }

@task(webhook_queue)
def process_webhook(webhook_data: Dict[str, Any], **kwargs):
    """Process webhook task implementation"""
    # Process webhook data
    webhook_type = webhook_data.get("type")
    
    if webhook_type == "stripe.payment.succeeded":
        logger.info("Stripe payment succeeded webhook received")
    elif webhook_type == "stripe.subscription.created":
        logger.info("Stripe subscription created webhook received")
    else:
        logger.info("Unhandled webhook type: %s", webhook_type)
    
    return {
        "success": True,
        "processed_type": webhook_type,
        "webhook_data": webhook_data
    }
