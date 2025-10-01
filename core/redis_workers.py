#!/usr/bin/env python3
"""
Redis Workers System
Background job processing with Redis queues, retries, and monitoring
"""

import os
import json
import time
import signal
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import threading
import multiprocessing

# Optional Redis integration
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

class WorkerStatus(Enum):
    """Worker status enumeration"""
    IDLE = "idle"
    PROCESSING = "processing"
    ERROR = "error"
    STOPPED = "stopped"

@dataclass
class WorkerJob:
    """Worker job data structure"""
    id: str
    task: str
    args: Dict[str, Any]
    priority: int
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    attempts: int = 0
    max_attempts: int = 3
    status: str = "pending"

class RedisWorker:
    """Redis-based background worker"""
    
    def __init__(self, worker_name: str, queue_name: str = "fikiri:jobs"):
        self.worker_name = worker_name
        self.queue_name = queue_name
        self.redis_client = None
        self.registered_tasks = {}
        self.status = WorkerStatus.IDLE
        self.current_job = None
        self.should_stop = False
        self.processed_jobs = 0
        self.failed_jobs = 0
        self.start_time = None
        self._connect_redis()
        self._initialize_tables()
    
    def _connect_redis(self):
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            logger.error("Redis not available, worker cannot start")
            return
        
        try:
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
            else:
                self.redis_client = redis.Redis(
                    host=os.getenv('REDIS_HOST', 'localhost'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    password=os.getenv('REDIS_PASSWORD'),
                    db=int(os.getenv('REDIS_DB', 0)),
                    decode_responses=True
                )
            
            self.redis_client.ping()
            logger.info(f"✅ Worker {self.worker_name} Redis connection established")
            
        except Exception as e:
            logger.error(f"❌ Worker {self.worker_name} Redis connection failed: {e}")
            self.redis_client = None
    
    def _initialize_tables(self):
        """Initialize database tables for worker tracking"""
        try:
            # Create worker jobs table
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS worker_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL UNIQUE,
                    worker_name TEXT NOT NULL,
                    task TEXT NOT NULL,
                    args TEXT DEFAULT '{}',
                    priority INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'pending',
                    attempts INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 3,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    started_at DATETIME,
                    completed_at DATETIME,
                    result TEXT,
                    error_message TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """, fetch=False)
            
            # Create worker status table
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS worker_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_name TEXT NOT NULL UNIQUE,
                    status TEXT DEFAULT 'idle',
                    current_job_id TEXT,
                    processed_jobs INTEGER DEFAULT 0,
                    failed_jobs INTEGER DEFAULT 0,
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_heartbeat DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                )
            """, fetch=False)
            
            # Create indexes
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_worker_jobs_status 
                ON worker_jobs (status)
            """, fetch=False)
            
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_worker_jobs_worker_name 
                ON worker_jobs (worker_name)
            """, fetch=False)
            
            logger.info(f"✅ Worker {self.worker_name} tables initialized")
            
        except Exception as e:
            logger.error(f"❌ Worker {self.worker_name} table initialization failed: {e}")
    
    def register_task(self, task_name: str, task_func: Callable):
        """Register a task function"""
        self.registered_tasks[task_name] = task_func
        logger.info(f"✅ Worker {self.worker_name} registered task: {task_name}")
    
    def enqueue_job(self, task: str, args: Dict[str, Any] = None, 
                   priority: int = 1, max_attempts: int = 3) -> str:
        """Enqueue a new job"""
        if not self.redis_client:
            raise Exception("Redis not available")
        
        try:
            job_id = f"{task}_{int(time.time())}_{self.worker_name}"
            args = args or {}
            
            job = WorkerJob(
                id=job_id,
                task=task,
                args=args,
                priority=priority,
                created_at=time.time(),
                max_attempts=max_attempts
            )
            
            # Store job in database
            db_optimizer.execute_query("""
                INSERT INTO worker_jobs 
                (job_id, worker_name, task, args, priority, max_attempts)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                self.worker_name,
                task,
                json.dumps(args),
                priority,
                max_attempts
            ), fetch=False)
            
            # Add to Redis queue
            job_data = {
                'id': job_id,
                'task': task,
                'args': args,
                'priority': priority,
                'created_at': job.created_at,
                'max_attempts': max_attempts
            }
            
            # Use priority queue
            self.redis_client.zadd(
                f"{self.queue_name}:pending",
                {json.dumps(job_data): priority}
            )
            
            logger.info(f"✅ Worker {self.worker_name} enqueued job: {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"❌ Worker {self.worker_name} job enqueue failed: {e}")
            raise
    
    def dequeue_job(self, timeout: int = 5) -> Optional[WorkerJob]:
        """Dequeue next job"""
        if not self.redis_client:
            return None
        
        try:
            # Get highest priority job
            result = self.redis_client.bzpopmax(
                f"{self.queue_name}:pending",
                timeout=timeout
            )
            
            if result:
                queue_name, job_data_str, score = result
                job_data = json.loads(job_data_str)
                
                job = WorkerJob(
                    id=job_data['id'],
                    task=job_data['task'],
                    args=job_data['args'],
                    priority=score,
                    created_at=job_data['created_at'],
                    max_attempts=job_data['max_attempts']
                )
                
                return job
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Worker {self.worker_name} job dequeue failed: {e}")
            return None
    
    def process_job(self, job: WorkerJob) -> bool:
        """Process a job"""
        try:
            self.status = WorkerStatus.PROCESSING
            self.current_job = job
            
            # Update job status
            db_optimizer.execute_query("""
                UPDATE worker_jobs 
                SET status = 'processing', started_at = datetime('now'), attempts = attempts + 1
                WHERE job_id = ?
            """, (job.id,), fetch=False)
            
            # Update worker status
            self._update_worker_status()
            
            # Get task function
            task_func = self.registered_tasks.get(job.task)
            if not task_func:
                raise Exception(f"Unknown task: {job.task}")
            
            # Execute task
            logger.info(f"🔄 Worker {self.worker_name} processing job {job.id}: {job.task}")
            result = task_func(**job.args)
            
            # Update job with result
            db_optimizer.execute_query("""
                UPDATE worker_jobs 
                SET status = 'completed', completed_at = datetime('now'), result = ?
                WHERE job_id = ?
            """, (json.dumps(result) if result else None, job.id), fetch=False)
            
            self.processed_jobs += 1
            logger.info(f"✅ Worker {self.worker_name} completed job {job.id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Worker {self.worker_name} job {job.id} failed: {e}")
            
            # Update job with error
            db_optimizer.execute_query("""
                UPDATE worker_jobs 
                SET status = 'failed', error_message = ?
                WHERE job_id = ?
            """, (str(e), job.id), fetch=False)
            
            self.failed_jobs += 1
            
            # Retry if attempts < max_attempts
            if job.attempts < job.max_attempts:
                logger.info(f"🔄 Worker {self.worker_name} retrying job {job.id}")
                self._retry_job(job)
            
            return False
        
        finally:
            self.status = WorkerStatus.IDLE
            self.current_job = None
            self._update_worker_status()
    
    def _retry_job(self, job: WorkerJob):
        """Retry a failed job"""
        try:
            # Calculate retry delay (exponential backoff)
            retry_delay = min(300 * (2 ** job.attempts), 3600)  # Max 1 hour
            
            # Schedule retry
            retry_time = time.time() + retry_delay
            
            job_data = {
                'id': job.id,
                'task': job.task,
                'args': job.args,
                'priority': job.priority,
                'created_at': job.created_at,
                'max_attempts': job.max_attempts,
                'attempts': job.attempts + 1
            }
            
            self.redis_client.zadd(
                f"{self.queue_name}:retry",
                {json.dumps(job_data): retry_time}
            )
            
            logger.info(f"⏰ Worker {self.worker_name} scheduled retry for job {job.id} in {retry_delay}s")
            
        except Exception as e:
            logger.error(f"❌ Worker {self.worker_name} retry scheduling failed: {e}")
    
    def _update_worker_status(self):
        """Update worker status in database"""
        try:
            db_optimizer.execute_query("""
                INSERT OR REPLACE INTO worker_status 
                (worker_name, status, current_job_id, processed_jobs, failed_jobs, last_heartbeat)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (
                self.worker_name,
                self.status.value,
                self.current_job.id if self.current_job else None,
                self.processed_jobs,
                self.failed_jobs
            ), fetch=False)
            
        except Exception as e:
            logger.error(f"❌ Worker {self.worker_name} status update failed: {e}")
    
    def start(self):
        """Start the worker"""
        if not self.redis_client:
            logger.error(f"❌ Worker {self.worker_name} cannot start: Redis not available")
            return
        
        self.should_stop = False
        self.start_time = time.time()
        self.status = WorkerStatus.IDLE
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info(f"🚀 Worker {self.worker_name} started")
        
        try:
            while not self.should_stop:
                try:
                    # Process retry queue
                    self._process_retry_queue()
                    
                    # Dequeue and process job
                    job = self.dequeue_job(timeout=5)
                    if job:
                        self.process_job(job)
                    else:
                        # No jobs available, sleep briefly
                        time.sleep(1)
                
                except Exception as e:
                    logger.error(f"❌ Worker {self.worker_name} processing error: {e}")
                    time.sleep(5)  # Wait before retrying
        
        except KeyboardInterrupt:
            logger.info(f"🛑 Worker {self.worker_name} interrupted")
        finally:
            self.status = WorkerStatus.STOPPED
            self._update_worker_status()
            logger.info(f"🛑 Worker {self.worker_name} stopped")
    
    def _process_retry_queue(self):
        """Process retry queue"""
        try:
            current_time = time.time()
            
            # Get jobs ready for retry
            retry_jobs = self.redis_client.zrangebyscore(
                f"{self.queue_name}:retry",
                0,
                current_time,
                withscores=True
            )
            
            for job_data_str, score in retry_jobs:
                try:
                    job_data = json.loads(job_data_str)
                    
                    # Move back to pending queue
                    self.redis_client.zadd(
                        f"{self.queue_name}:pending",
                        {job_data_str: job_data['priority']}
                    )
                    
                    # Remove from retry queue
                    self.redis_client.zrem(f"{self.queue_name}:retry", job_data_str)
                    
                    logger.info(f"🔄 Worker {self.worker_name} moved job {job_data['id']} back to pending")
                    
                except Exception as e:
                    logger.error(f"❌ Worker {self.worker_name} retry processing failed: {e}")
        
        except Exception as e:
            logger.error(f"❌ Worker {self.worker_name} retry queue processing failed: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"🛑 Worker {self.worker_name} received signal {signum}")
        self.should_stop = True
    
    def stop(self):
        """Stop the worker"""
        self.should_stop = True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        try:
            uptime = time.time() - self.start_time if self.start_time else 0
            
            return {
                'worker_name': self.worker_name,
                'status': self.status.value,
                'current_job': self.current_job.id if self.current_job else None,
                'processed_jobs': self.processed_jobs,
                'failed_jobs': self.failed_jobs,
                'uptime': uptime,
                'start_time': self.start_time,
                'registered_tasks': list(self.registered_tasks.keys())
            }
            
        except Exception as e:
            logger.error(f"❌ Worker {self.worker_name} stats failed: {e}")
            return {}

class WorkerManager:
    """Manager for multiple Redis workers"""
    
    def __init__(self):
        self.workers = {}
        self.worker_threads = {}
    
    def create_worker(self, worker_name: str, queue_name: str = "fikiri:jobs") -> RedisWorker:
        """Create a new worker"""
        worker = RedisWorker(worker_name, queue_name)
        self.workers[worker_name] = worker
        return worker
    
    def start_worker(self, worker_name: str):
        """Start a worker in a separate thread"""
        if worker_name not in self.workers:
            raise Exception(f"Worker {worker_name} not found")
        
        worker = self.workers[worker_name]
        
        # Start worker in thread
        thread = threading.Thread(target=worker.start, daemon=True)
        thread.start()
        self.worker_threads[worker_name] = thread
        
        logger.info(f"🚀 Started worker {worker_name} in thread")
    
    def stop_worker(self, worker_name: str):
        """Stop a worker"""
        if worker_name in self.workers:
            self.workers[worker_name].stop()
        
        if worker_name in self.worker_threads:
            thread = self.worker_threads[worker_name]
            thread.join(timeout=10)
            del self.worker_threads[worker_name]
        
        logger.info(f"🛑 Stopped worker {worker_name}")
    
    def stop_all_workers(self):
        """Stop all workers"""
        for worker_name in list(self.workers.keys()):
            self.stop_worker(worker_name)
    
    def get_worker_stats(self, worker_name: str = None) -> Dict[str, Any]:
        """Get worker statistics"""
        if worker_name:
            if worker_name in self.workers:
                return self.workers[worker_name].get_stats()
            else:
                return {'error': f'Worker {worker_name} not found'}
        else:
            return {
                worker_name: worker.get_stats()
                for worker_name, worker in self.workers.items()
            }

# Global worker manager
worker_manager = WorkerManager()

# Create default workers
email_worker = worker_manager.create_worker("email_worker", "fikiri:email:jobs")
gmail_sync_worker = worker_manager.create_worker("gmail_sync_worker", "fikiri:gmail:sync")
ai_worker = worker_manager.create_worker("ai_worker", "fikiri:ai:jobs")
crm_worker = worker_manager.create_worker("crm_worker", "fikiri:crm:jobs")

# Register default tasks
def send_email_task(to: str, subject: str, body: str, **kwargs):
    """Send email task"""
    from core.email_jobs import email_job_manager
    return email_job_manager.process_jobs(max_jobs=1)

def gmail_sync_task(user_id: int, sync_type: str = 'full', **kwargs):
    """Gmail sync task"""
    from core.gmail_sync_jobs import gmail_sync_job_manager
    job_id = gmail_sync_job_manager.queue_sync_job(user_id, sync_type)
    return gmail_sync_job_manager.process_sync_job(job_id)

def ai_processing_task(user_id: int, task_type: str, data: Dict[str, Any], **kwargs):
    """AI processing task"""
    # Placeholder for AI processing
    return {'success': True, 'result': 'AI processing completed'}

def crm_sync_task(user_id: int, sync_type: str = 'full', **kwargs):
    """CRM sync task"""
    # Placeholder for CRM sync
    return {'success': True, 'result': 'CRM sync completed'}

# Register tasks
email_worker.register_task('send_email', send_email_task)
gmail_sync_worker.register_task('gmail_sync', gmail_sync_task)
ai_worker.register_task('ai_processing', ai_processing_task)
crm_worker.register_task('crm_sync', crm_sync_task)

# Start workers
def start_all_workers():
    """Start all workers"""
    worker_manager.start_worker("email_worker")
    worker_manager.start_worker("gmail_sync_worker")
    worker_manager.start_worker("ai_worker")
    worker_manager.start_worker("crm_worker")
    logger.info("🚀 All workers started")

def stop_all_workers():
    """Stop all workers"""
    worker_manager.stop_all_workers()
    logger.info("🛑 All workers stopped")
