#!/usr/bin/env python3
"""
RQ Worker Script
Processes background jobs from Redis queues

Usage:
    python scripts/rq_worker.py [queue_name]
    
    Queue names: email, ai, crm (default: all)
"""

import os
import sys
import logging
import signal
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def register_tasks():
    """Register all task functions with queues"""
    from core.redis_queues import (
        email_queue, ai_queue, crm_queue,
        get_email_queue, get_ai_queue, get_crm_queue
    )
    from email_automation.gmail_sync_jobs import GmailSyncJobManager
    
    # Register Gmail sync task
    sync_job_manager = GmailSyncJobManager()
    email_queue.register_task('process_gmail_sync', sync_job_manager.process_sync_job)
    
    # Register email sending task (if exists)
    try:
        from email_automation.actions import MinimalEmailActions
        email_actions = MinimalEmailActions()
        email_queue.register_task('send_email', email_actions.send_email)
    except Exception as e:
        logger.warning(f"Could not register send_email task: {e}")
    
    # Register AI processing task
    try:
        from email_automation.ai_assistant import MinimalAIEmailAssistant
        ai_assistant = MinimalAIEmailAssistant()
        ai_queue.register_task('process_ai_request', ai_assistant.process_request)
    except Exception as e:
        logger.warning(f"Could not register AI task: {e}")
    
    # Register CRM update task
    try:
        from crm.service import enhanced_crm_service
        def update_crm_task(lead_data: dict, **kwargs):
            user_id = lead_data.get('user_id', 1)
            return enhanced_crm_service.create_lead(user_id, lead_data)
        crm_queue.register_task('update_crm', update_crm_task)
    except Exception as e:
        logger.warning(f"Could not register CRM task: {e}")
    
    logger.info("✅ All tasks registered")

def start_worker(queue_name: Optional[str] = None):
    """Start RQ worker for specified queue"""
    from core.redis_queues import (
        email_queue, ai_queue, crm_queue,
        start_worker as rq_start_worker
    )
    
    # Register tasks first
    register_tasks()
    
    # Select queue(s)
    if queue_name:
        queue_map = {
            'email': email_queue,
            'ai': ai_queue,
            'crm': crm_queue
        }
        if queue_name not in queue_map:
            logger.error(f"Unknown queue: {queue_name}. Available: {list(queue_map.keys())}")
            sys.exit(1)
        queues = [queue_map[queue_name]]
        worker_name = f"rq-worker-{queue_name}"
    else:
        # Process all queues
        queues = [email_queue, ai_queue, crm_queue]
        worker_name = "rq-worker-all"
    
    logger.info(f"🚀 Starting {worker_name}")
    
    # Handle graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"🛑 Received signal {sig}, shutting down gracefully...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start workers (one per queue)
    import threading
    
    def run_worker(queue, name):
        try:
            rq_start_worker(queue, name)
        except Exception as e:
            logger.error(f"❌ Worker {name} error: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    threads = []
    for queue in queues:
        thread = threading.Thread(
            target=run_worker,
            args=(queue, f"{worker_name}-{queue.queue_name}"),
            daemon=True
        )
        thread.start()
        threads.append(thread)
        logger.info(f"✅ Started worker thread for {queue.queue_name}")
    
    # Keep main thread alive
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down workers...")
        sys.exit(0)

if __name__ == "__main__":
    queue_name = sys.argv[1] if len(sys.argv) > 1 else None
    start_worker(queue_name)
