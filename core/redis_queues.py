#!/usr/bin/env python3
"""
Redis Queues for Background Jobs - Fikiri Solutions
Async task processing with Redis as message broker
"""

import json
import time
import uuid
import logging
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass

# Optional Redis integration
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

try:
    from core.minimal_config import get_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    get_config = None

logger = logging.getLogger(__name__)

class JobStatus(Enum):
    """Job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

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

class RedisQueue:
    """Redis-based job queue system"""
    
    def __init__(self, queue_name: str = "fikiri:jobs"):
        self.config = get_config()
        self.redis_client = None
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
            if self.config.redis_url:
                self.redis_client = redis.from_url(
                    self.config.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            else:
                self.redis_client = redis.Redis(
                    host=self.config.redis_host,
                    port=self.config.redis_port,
                    password=self.config.redis_password,
                    db=self.config.redis_db,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            
            self.redis_client.ping()
            logger.info(f"✅ Redis queue '{self.queue_name}' connected")
            
        except Exception as e:
            logger.error(f"❌ Redis queue connection failed: {e}")
            self.redis_client = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
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
            
            # Get next pending job
            if timeout > 0:
                result = self.redis_client.brpop(f"{self.queue_name}:pending", timeout)
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
            logger.error(f"❌ Job dequeue failed: {e}")
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
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Job completion failed: {e}")
            return False
    
    def fail_job(self, job_id: str, error: str, retry: bool = True):
        """Mark job as failed"""
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
                
                if retry and job.retry_count <= job.max_retries:
                    # Retry job
                    job.status = JobStatus.RETRYING
                    self.redis_client.lpush(f"{self.queue_name}:pending", job_id)
                    logger.info(f"🔄 Retrying job {job_id} (attempt {job.retry_count})")
                else:
                    # Mark as failed
                    job.status = JobStatus.FAILED
                    job.completed_at = time.time()
                    logger.info(f"❌ Failed job {job_id}: {error}")
                
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

def get_email_queue() -> RedisQueue:
    """Get email processing queue"""
    return email_queue

def get_ai_queue() -> RedisQueue:
    """Get AI processing queue"""
    return ai_queue

def get_crm_queue() -> RedisQueue:
    """Get CRM processing queue"""
    return crm_queue

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
    
    while True:
        try:
            job = queue.dequeue_job(timeout=5)
            if job:
                logger.info(f"📋 Processing job {job.id}: {job.task}")
                
                # Get task function
                task_func = queue._registered_tasks.get(job.task)
                if task_func:
                    try:
                        result = task_func(**job.args)
                        queue.complete_job(job.id, result)
                        logger.info(f"✅ Completed job {job.id}")
                    except Exception as e:
                        queue.fail_job(job.id, str(e))
                        logger.error(f"❌ Failed job {job.id}: {e}")
                else:
                    queue.fail_job(job.id, f"Unknown task: {job.task}")
                    logger.error(f"❌ Unknown task: {job.task}")
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
    from core.minimal_email_actions import MinimalEmailActions
    
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
    from core.minimal_ai_assistant import MinimalAIAssistant
    
    ai_service = MinimalAIAssistant()
    result = ai_service.process_request(prompt, user_id)
    
    return {
        "success": True,
        "response": result,
        "user_id": user_id
    }

@task(crm_queue)
def update_crm(lead_data: Dict[str, Any], **kwargs):
    """Update CRM task implementation"""
    # Import your CRM service here
    from core.minimal_crm_service import MinimalCRMService
    
    crm_service = MinimalCRMService()
    result = crm_service.add_lead(lead_data)
    
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
        # Handle successful payment
        pass
    elif webhook_type == "stripe.subscription.created":
        # Handle new subscription
        pass
    
    return {
        "success": True,
        "processed_type": webhook_type,
        "webhook_data": webhook_data
    }
