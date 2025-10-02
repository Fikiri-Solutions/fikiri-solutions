#!/usr/bin/env python3
"""
Onboarding Background Jobs with RQ
Production-grade background job processing for email sync and onboarding
Based on proven RQ patterns with progress tracking
"""

import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Try to import RQ for background jobs
try:
    from rq import Queue, Worker
    REDIS_QUEUE_AVAILABLE = True
except ImportError:
    REDIS_QUEUE_AVAILABLE = False
    logger.warning("⚠️ RQ not available, jobs will run synchronously")

# Try to import Redis
try:
    from redis import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("⚠️ Redis not available, using in-memory storage")

# Try to import CRM and Gmail client
try:
    from core.gmail_client import gmail_client
    GMAIL_CLIENT_AVAILABLE = True
except ImportError:
    GMAIL_CLIENT_AVAILABLE = False
    logger.warning("⚠️ Gmail client not available")

class OnboardingJobManager:
    """Manages onboarding background jobs with progress tracking"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        self.redis_client = None
        self.queue = None
        
        if REDIS_AVAILABLE and self.redis_url:
            try:
                self.redis_client = Redis.from_url(self.redis_url, decode_responses=True)
                self.redis_client.ping()
                
                if REDIS_QUEUE_AVAILABLE:
                    self.queue = Queue("onboarding", connection=self.redis_client)
                    
                logger.info("✅ Onboarding job manager initialized with Redis")
                
            except Exception as e:
                logger.error(f"❌ Redis connection failed: {e}")
                self.redis_client = None
                self.queue = None
        else:
            logger.warning("⚠️ Onboarding jobs will run without Redis")
    
    def queue_first_sync_job(self, user_id: int) -> Dict[str, Any]:
        """Queue first email sync job for user"""
        try:
            if REDIS_QUEUE_AVAILABLE and self.queue:
                # Queue background job
                job = self.queue.enqueue(
                    run_first_sync, 
                    user_id,
                    depends_on=None,
                    job_timeout=900,  # 15 minutes
                    job_id=f"first_sync_{user_id}_{int(time.time())}"
                )
                
                logger.info(f"✅ Queued first sync job {job.id} for user {user_id}")
                
                return {
                    "success": True,
                    "job_id": job.id,
                    "message": "Sync job queued successfully"
                }
            else:
                # Run synchronously if RQ not available
                logger.info(f"🔄 Running first sync synchronously for user {user_id}")
                result = run_first_sync(user_id)
                
                return {
                    "success": True,
                    "job_id": f"sync_{user_id}_{int(time.time())}",
                    "message": "Sync completed synchronously",
                    "result": result
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to queue sync job for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "JOB_QUEUE_FAILED"
            }
    
    def get_sync_progress(self, user_id: int) -> Dict[str, Any]:
        """Get sync progress for user"""
        try:
            if self.redis_client:
                # Read progress from Redis
                prog_key = f"onboarding:{user_id}:progress"
                progress_data = self.redis_client.hgetall(prog_key)
                
                if progress_data:
                    return {
                        "success": True,
                        "progress": {
                            "step": progress_data.get("step", "starting"),
                            "percentage": int(progress_data.get("pct", "0")),
                            "total": int(progress_data.get("total", "0")),
                            "processed": int(progress_data.get("processed", "0")),
                            "status": progress_data.get("status", "running")
                        }
                    }
                else:
                    return {
                        "success": True,
                        "progress": {
                            "step": "none",
                            "percentage": 0,
                            "total": 0,
                            "processed": 0,
                            "status": "not_started"
                        }
                    }
            else:
                return {
                    "success": False,
                    "error": "Redis not available",
                    "error_code": "REDIS_UNAVAILABLE"
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get sync progress for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "PROGRESS_RETRIEVE_FAILED"
            }

# Global job manager instance
onboarding_job_manager = OnboardingJobManager()

def run_first_sync(user_id: int, limit: int = 500, newer_than_days: int = 90) -> Dict[str, Any]:
    """
    Run first Gmail sync for user (bounded and idempotent)
    Based on proven patterns that avoid timeouts and rate limits
    """
    try:
        logger.info(f"🔄 Starting first sync for user {user_id}")
        
        # Initialize Redis for progress tracking
        redis_client = None
        if REDIS_AVAILABLE and os.getenv("REDIS_URL"):
            try:
                redis_client = Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
            except Exception as e:
                logger.warning(f"⚠️ Redis connection failed: {e}")
        
        # Set initial progress
        prog_key = f"onboarding:{user_id}:progress"
        if redis_client:
            redis_client.hset(prog_key, mapping={"step": "starting", "pct": "2"})
        
        # Get Gmail service
        if not GMAIL_CLIENT_AVAILABLE or not gmail_client:
            raise RuntimeError("Gmail client not available")
            
        svc = gmail_client.get_gmail_service_for_user(user_id)
        if redis_client:
            redis_client.hset(prog_key, mapping={"step": "fetching", "pct": "10"})
        
        # Fetch recent messages (bounded strategy)
        logger.info(f"📧 Fetching messages newer than {newer_than_days} days")
        after_date = datetime.utcnow() - timedelta(days=newer_than_days)
        after_timestamp = int(after_date.timestamp())
        
        search_query = f"after:{after_timestamp}"
        
        msg_ids = []
        page_token = None
        
        # Fetch message IDs with pagination
        while len(msg_ids) < limit:
            try:
                response = svc.users().messages().list(
                    userId="me",
                    q=search_query,
                    pageToken=page_token,
                    maxResults=min(100, limit - len(msg_ids))
                ).execute()
                
                new_ids = [msg["id"] for msg in response.get("messages", [])]
                msg_ids.extend(new_ids)
                
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
                    
                logger.info(f"📧 Fetched {len(msg_ids)} message IDs so far")
                
            except Exception as e:
                logger.error(f"❌ Failed to fetch message list: {e}")
                break
        
        logger.info(f"✅ Found {len(msg_ids)} messages to process")
        
        if redis_client:
            redis_client.hset(prog_key, mapping={
                "step": "parsing",
                "pct": "30",
                "total": str(len(msg_ids))
            })
        
        # Process messages with simple lead extraction
        seen_key = f"seen:{user_id}"  # Redis set for idempotency
        processed = 0
        leads_created = 0
        
        logger.info(f"🔄 Processing {len(msg_ids)} messages")
        
        for idx, msg_id in enumerate(msg_ids, start=1):
            try:
                # Check idempotency
                if redis_client and redis_client.sismember(seen_key, msg_id):
                    continue
                
                # Get message metadata
                message = svc.users().messages().get(
                    userId="me",
                    id=msg_id,
                    format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date"]
                ).execute()
                
                # Extract headers
                headers = message.get("payload", {}).get("headers", [])
                header_dict = {h["name"].lower(): h["value"] for h in headers}
                
                # Simple lead extraction
                from_email = header_dict.get("from", "")
                subject = header_dict.get("subject", "")
                
                # Basic email parsing
                if from_email:
                    email_address = extract_email_from_address(from_email)
                    name = extract_name_from_address(from_email)
                    
                    if email_address:
                        # Create lead in CRM
                        lead_data = {
                            "email": email_address,
                            "name": name or "",
                            "subject": subject,
                            "source": "gmail",
                            "external_id": msg_id,
                            "stage": "new"
                        }
                        
                        # Upsert lead (implement your CRM logic)
                        if upsert_lead(user_id, lead_data):
                            leads_created += 1
                
                # Mark as processed
                if redis_client:
                    pipeline = redis_client.pipeline()
                    pipeline.sadd(seen_key, msg_id)
                    pipeline.execute()
                
                processed += 1
                
                # Update progress every 25 messages
                if idx % 25 == 0:
                    progress_pct = 30 + int(60 * idx / len(msg_ids))
                    if redis_client:
                        redis_client.hset(prog_key, mapping={
                            "step": "parsing",
                            "pct": str(progress_pct),
                            "processed": str(processed)
                        })
                    logger.info(f"📊 Processed {idx}/{len(msg_ids)} messages ({progress_pct}%)")
                
            except Exception as e:
                logger.error(f"❌ Failed to process message {msg_id}: {e}")
                continue
        
        # Complete sync
        logger.info(f"✅ Sync completed: {processed} processed, {leads_created} leads created")
        
        final_progress = {
            "step": "done",
            "pct": "100",
            "processed": str(processed),
            "leads_created": str(leads_created),
            "status": "completed"
        }
        
        if redis_client:
            redis_client.hset(prog_key, mapping=final_progress)
            # Set TTL for cleanup
            redis_client.expire(prog_key, 3600)  # 1 hour
        
        return {
            "success": True,
            "processed": processed,
            "leads_created": leads_created,
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"❌ First sync failed for user {user_id}: {e}")
        
        # Set error progress
        prog_key = f"onboarding:{user_id}:progress"
        error_progress = {
            "step": "error",
            "pct": "0",
            "status": "failed",
            "error": str(e)
        }
        
        # Update Redis if available
        if REDIS_AVAILABLE and os.getenv("REDIS_URL"):
            try:
                import redis
                redis_client = redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
                redis_client.hset(prog_key, mapping=error_progress)
            except Exception as redis_e:
                logger.error(f"❌ Failed to update Redis with error: {redis_e}")
        
        return {
            "success": False,
            "error": str(e),
            "processed": 0,
            "leads_created": 0,
            "status": "failed"
        }

def extract_email_from_address(address: str) -> Optional[str]:
    """Extract email from From address"""
    try:
        import re
        # Handle "Name <email@domain.com>" format
        email_match = re.search(r'<([^>]+)>', address)
        if email_match:
            return email_match.group(1).strip()
        
        # Handle plain email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', address)
        if email_match:
            return email_match.group(0).strip()
            
        return None
    except Exception:
        return None

def extract_name_from_address(address: str) -> Optional[str]:
    """Extract name from From address"""
    try:
        import re
        # Extract name from "Name <email@domain.com>" format
        name_match = re.search(r'^([^<]+)<', address)
        if name_match:
            name = name_match.group(1).strip()
            # Clean up common prefixes
            name = name.strip('"').strip("'")
            return name if name else None
        return None
    except Exception:
        return None

def upsert_lead(user_id: int, lead_data: Dict[str, Any]) -> bool:
    """Create or update lead in CRM"""
    try:
        from core.database_optimization import db_optimizer
        
        # Check if lead already exists
        existing = db_optimizer.execute_query(
            "SELECT id FROM leads WHERE user_id = ? AND external_id = ?",
            (user_id, lead_data.get("external_id"))
        )
        
        if existing:
            # Update existing lead
            db_optimizer.execute_query("""
                UPDATE leads 
                SET email = ?, name = ?, subject = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND external_id = ?
            """, (
                lead_data["email"],
                lead_data.get("name", ""),
                lead_data.get("subject", ""),
                user_id,
                lead_data.get("external_id")
            ), fetch=False)
        else:
            # Create new lead
            db_optimizer.execute_query("""
                INSERT INTO leads 
                (user_id, email, name, subject, source, external_id, stage, 
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                user_id,
                lead_data["email"],
                lead_data.get("name", ""),
                lead_data.get("subject", ""),
                lead_data.get("source", "gmail"),
                lead_data.get("external_id"),
                lead_data.get("stage", "new")
            ), fetch=False)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to upsert lead: {e}")
        return False
