#!/usr/bin/env python3
"""
Gmail Sync Background Jobs
Background processing for Gmail email synchronization with Redis queues
"""

import os
import json
import time
import sys
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

# Optional Redis integration
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

# Optional Gmail API integration
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    GMAIL_API_AVAILABLE = True
except ImportError:
    GMAIL_API_AVAILABLE = False

from core.database_optimization import db_optimizer
from integrations.gmail.gmail_client import gmail_client

logger = logging.getLogger(__name__)


def should_process_gmail_sync_inline() -> bool:
    """
    Run Gmail sync in the web process (daemon thread) instead of the Redis job queue.

    On Render, SQLite lives on the web service disk (`DATABASE_URL=sqlite:///...`).
    A separate background worker cannot mount that disk, so queued jobs are never
    processed and sync stays at 0–1%. PostgreSQL (or explicit opt-in) can use Redis workers.
    """
    db_url = (os.getenv("DATABASE_URL") or "").strip().lower()
    if "sqlite" in db_url:
        return True
    force = (os.getenv("GMAIL_SYNC_FORCE_INLINE") or "").strip().lower()
    if force in ("1", "true", "yes", "on"):
        return True
    return False


def _is_test_mode() -> bool:
    return (
        os.getenv("FIKIRI_TEST_MODE") == "1"
        or os.getenv("FLASK_ENV") == "test"
        or bool(os.getenv("PYTEST_CURRENT_TEST"))
    )


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

class SyncStatus(Enum):
    """Sync status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

@dataclass
class EmailMessage:
    """Email message data structure"""
    id: str
    thread_id: str
    subject: str
    sender: str
    recipient: str
    date: datetime
    body: str
    labels: List[str]
    attachments: List[Dict[str, Any]]

@dataclass
class Contact:
    """Contact data structure"""
    email: str
    name: str
    company: str
    last_contact: datetime
    contact_count: int
    lead_score: int

class GmailSyncJobManager:
    """Gmail synchronization job management system"""
    
    def __init__(self):
        self.redis_client = None
        self.queue_name = "fikiri:gmail:sync"
        self.failed_queue_name = "fikiri:gmail:failed"
        # Per-request page size (Gmail allows up to 500; we page with nextPageToken).
        self.sync_page_size = min(500, max(1, int(os.getenv('GMAIL_SYNC_PAGE_SIZE', '100'))))
        # Max messages to pull per sync job (after pagination). Was a single-page cap of 50 — caused “missing” mail.
        self.sync_max_messages = max(1, int(os.getenv('GMAIL_SYNC_MAX_MESSAGES', '500')))
        self.sync_days = int(os.getenv('GMAIL_SYNC_DAYS', '90'))  # Align with onboarding-style window
        self._connect_redis()
        self._initialize_tables()
    
    def _connect_redis(self):
        """Connect to Redis for job queues"""
        if _is_test_mode():
            self.redis_client = None
            return
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, Gmail sync jobs will be processed synchronously")
            return
        
        try:
            from core.redis_connection_helper import get_redis_client
            self.redis_client = get_redis_client(decode_responses=True, db=int(os.getenv('REDIS_DB', 0)))
            if self.redis_client:
                logger.info("✅ Gmail sync Redis connection established")
            else:
                logger.warning("⚠️ Redis connection failed, Gmail sync jobs will be processed synchronously")
        except Exception as e:
            logger.error(f"❌ Gmail sync Redis connection failed: {e}")
            self.redis_client = None
    
    def _initialize_tables(self):
        """Initialize database tables for Gmail sync tracking"""
        try:
            # Create Gmail sync jobs table
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS gmail_sync_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    job_id TEXT NOT NULL UNIQUE,
                    status TEXT DEFAULT 'pending',
                    progress INTEGER DEFAULT 0,
                    emails_synced INTEGER DEFAULT 0,
                    contacts_found INTEGER DEFAULT 0,
                    leads_identified INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    started_at DATETIME,
                    completed_at DATETIME,
                    error_message TEXT,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """, fetch=False)
            
            # Create synced emails table (supports multiple providers)
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS synced_emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    gmail_id TEXT,  -- Legacy Gmail ID (for backward compatibility)
                    external_id TEXT,  -- Generic external ID (Gmail, Outlook, etc.)
                    provider TEXT DEFAULT 'gmail',  -- 'gmail', 'outlook', etc.
                    thread_id TEXT,
                    subject TEXT,
                    sender TEXT,
                    recipient TEXT,
                    date DATETIME,
                    body TEXT,
                    labels TEXT DEFAULT '[]',
                    attachments TEXT DEFAULT '[]',
                    processed BOOLEAN DEFAULT FALSE,
                    is_read BOOLEAN DEFAULT FALSE,
                    lead_score INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, external_id, provider)
                )
            """, fetch=False)
            
            # Migration: add columns when missing (idempotent; matches core/database_optimization).
            try:
                cols = set(db_optimizer.list_table_columns("synced_emails") or [])
                if cols and "provider" not in cols:
                    db_optimizer.execute_query(
                        "ALTER TABLE synced_emails ADD COLUMN provider TEXT DEFAULT 'gmail'",
                        fetch=False,
                    )
                    logger.info("✅ Added provider column to synced_emails (gmail_sync_jobs migration)")
                if cols and "is_read" not in cols:
                    db_optimizer.execute_query(
                        "ALTER TABLE synced_emails ADD COLUMN is_read BOOLEAN DEFAULT 0",
                        fetch=False,
                    )
            except Exception as mig_err:
                logger.debug("synced_emails column migration skipped: %s", mig_err)
            try:
                db_optimizer.execute_query("""
                    UPDATE synced_emails 
                    SET external_id = gmail_id, provider = 'gmail'
                    WHERE external_id IS NULL AND gmail_id IS NOT NULL
                """, fetch=False)
            except Exception as e:
                if "no such column: provider" in str(e).lower():
                    try:
                        db_optimizer.execute_query(
                            "ALTER TABLE synced_emails ADD COLUMN provider TEXT DEFAULT 'gmail'",
                            fetch=False,
                        )
                        db_optimizer.execute_query("""
                            UPDATE synced_emails 
                            SET external_id = gmail_id, provider = 'gmail'
                            WHERE external_id IS NULL AND gmail_id IS NOT NULL
                        """, fetch=False)
                    except Exception as retry_err:
                        logger.warning("synced_emails provider backfill failed: %s", retry_err)
                else:
                    logger.warning(f"Migration note: {e}")
            
            # Create contacts table
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    email TEXT NOT NULL,
                    name TEXT,
                    company TEXT,
                    last_contact DATETIME,
                    contact_count INTEGER DEFAULT 1,
                    lead_score INTEGER DEFAULT 0,
                    source TEXT DEFAULT 'gmail',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, email)
                )
            """, fetch=False)
            
            # Create indexes
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_gmail_sync_jobs_user_id 
                ON gmail_sync_jobs (user_id)
            """, fetch=False)
            
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_synced_emails_user_id 
                ON synced_emails (user_id)
            """, fetch=False)
            
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_contacts_user_id 
                ON contacts (user_id)
            """, fetch=False)
            
            # Create user_sync_status table for tracking sync state
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS user_sync_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    last_sync DATETIME,
                    sync_status TEXT DEFAULT 'connected_pending_sync',
                    syncing INTEGER DEFAULT 0,
                    total_emails INTEGER DEFAULT 0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """, fetch=False)
            
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_user_sync_status_user_id 
                ON user_sync_status (user_id)
            """, fetch=False)
            
            logger.info("✅ Gmail sync tables initialized")
            
        except Exception as e:
            logger.error(f"❌ Gmail sync table initialization failed: {e}")
    
    def queue_sync_job(self, user_id: int, sync_type: str = 'full', 
                      metadata: Dict[str, Any] = None) -> str:
        """Queue a Gmail sync job for a user"""
        try:
            job_id = f"gmail_sync_{user_id}_{int(time.time())}"
            
            # Create job record
            db_optimizer.execute_query("""
                INSERT INTO gmail_sync_jobs 
                (user_id, job_id, status, metadata)
                VALUES (?, ?, 'pending', ?)
            """, (
                user_id,
                job_id,
                json.dumps(metadata or {})
            ), fetch=False)
            
            # Update user_sync_status to show pending sync
            try:
                db_optimizer.upsert_user_sync_status_merge(
                    user_id, sync_status="pending", syncing=0
                )
                logger.info(f"✅ Updated user_sync_status to 'pending' for user {user_id}")
            except Exception as status_error:
                logger.warning(f"⚠️ Could not update user_sync_status to pending: {status_error}")
            
            # Optional: mirror job id on legacy Redis list (only when not using inline web-thread mode)
            if self.redis_client and not should_process_gmail_sync_inline():
                job_data = {
                    'job_id': job_id,
                    'user_id': user_id,
                    'sync_type': sync_type,
                    'metadata': metadata or {},
                    'created_at': time.time()
                }
                
                self.redis_client.lpush(f"{self.queue_name}:pending", json.dumps(job_data))
            
            logger.info(f"✅ Queued Gmail sync job: {job_id} for user {user_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"❌ Gmail sync job queuing failed: {e}")
            return None
    
    def process_sync_job(self, job_id: str, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """Process a Gmail sync job"""
        # Set trace ID if provided
        try:
            from core.trace_context import set_trace_id, get_trace_id
            if trace_id:
                set_trace_id(trace_id)
            else:
                trace_id = get_trace_id()
        except ImportError:
            trace_id = trace_id or str(uuid.uuid4())
        
        logger.info(f"🔄 Starting to process sync job: {job_id}", extra={
            'event': 'gmail_sync_started',
            'service': 'email',
            'severity': 'INFO',
            'trace_id': trace_id,
            'job_id': job_id
        })
        try:
            # Get job details
            job_data = db_optimizer.execute_query("""
                SELECT id, user_id, job_id, status, progress, emails_synced, contacts_found, leads_identified, created_at, started_at, completed_at, error_message, metadata FROM gmail_sync_jobs WHERE job_id = ?
            """, (job_id,))
            
            if not job_data:
                logger.error(f"❌ Job {job_id} not found in database")
                return {
                    'success': False,
                    'error': 'Job not found',
                    'error_code': 'JOB_NOT_FOUND'
                }
            
            job = job_data[0]
            user_id = job['user_id']
            logger.info(f"📋 Processing sync job {job_id} for user {user_id}")
            
            # Update job status
            db_optimizer.execute_query("""
                UPDATE gmail_sync_jobs 
                SET status = 'processing', started_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, (job_id,), fetch=False)
            logger.info(f"✅ Updated job {job_id} status to 'processing'")
            
            # Update user_sync_status to show syncing in progress
            try:
                db_optimizer.upsert_user_sync_status_merge(
                    user_id,
                    last_sync=_utcnow_naive().isoformat(),
                    sync_status="in_progress",
                    syncing=1,
                )
            except Exception as status_error:
                logger.warning(f"⚠️ Could not update user_sync_status to in_progress: {status_error}")
            
            # Get Gmail service (handles token refresh automatically)
            if not GMAIL_API_AVAILABLE:
                raise Exception("Gmail API not available")
            
            # Use gmail_client to get service with automatic token refresh
            service = gmail_client.get_gmail_service_for_user(user_id)
            
            # Sync emails
            sync_result = self._sync_emails(service, user_id, job_id)
            
            # Update job with results - ensure progress is 100% when completed
            final_progress = 100
            db_optimizer.execute_query("""
                UPDATE gmail_sync_jobs 
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP,
                    progress = ?, emails_synced = ?, contacts_found = ?, leads_identified = ?
                WHERE job_id = ?
            """, (
                final_progress,
                sync_result['emails_synced'],
                sync_result['contacts_found'],
                sync_result['leads_identified'],
                job_id
            ), fetch=False)
            logger.info(f"✅ Updated job {job_id} to completed with progress={final_progress}%")
            
            # Update user_sync_status to reflect completed sync
            try:
                total_emails = sync_result.get('emails_synced', 0)
                db_optimizer.upsert_user_sync_status_completed(user_id, total_emails)
                logger.info(f"✅ Updated user_sync_status for user {user_id}")
            except Exception as status_error:
                logger.warning(f"⚠️ Could not update user_sync_status: {status_error}")
            
            logger.info(f"✅ Completed Gmail sync job: {job_id}")
            
            return {
                'success': True,
                'job_id': job_id,
                'emails_synced': sync_result['emails_synced'],
                'contacts_found': sync_result['contacts_found'],
                'leads_identified': sync_result['leads_identified']
            }
            
        except Exception as e:
            logger.error(f"❌ Gmail sync job processing failed: {e}")
            
            # Update job with error
            try:
                db_optimizer.execute_query("""
                    UPDATE gmail_sync_jobs 
                    SET status = 'failed', error_message = ?
                    WHERE job_id = ?
                """, (str(e), job_id), fetch=False)
            except Exception as update_error:
                logger.warning("⚠️ Could not update gmail_sync_jobs failure status: %s", update_error)
            
            # Update user_sync_status to reflect failed sync
            try:
                job = job_data[0] if 'job_data' in locals() and job_data else None
                user_id = job['user_id'] if job else None
                if user_id:
                    db_optimizer.upsert_user_sync_status_merge(
                        user_id,
                        last_sync=_utcnow_naive().isoformat(),
                        sync_status="failed",
                        syncing=0,
                    )
                    logger.info(f"✅ Updated user_sync_status to 'failed' for user {user_id}")
            except Exception as status_error:
                logger.warning(f"⚠️ Could not update user_sync_status on error: {status_error}")
            
            return {
                'success': False,
                'error': str(e),
                'error_code': 'SYNC_PROCESSING_FAILED'
            }
    
    def _sync_emails(self, service, user_id: int, job_id: str) -> Dict[str, Any]:
        """Sync emails from Gmail"""
        try:
            # Update initial progress to show sync has started
            db_optimizer.execute_query("""
                UPDATE gmail_sync_jobs 
                SET progress = 5, status = 'processing', started_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, (job_id,), fetch=False)
            logger.info(f"📊 Sync job {job_id} started - progress set to 5%")
            
            # Get messages from Gmail
            messages = self._get_gmail_messages(service)
            
            # Update progress after fetching message list
            if messages:
                db_optimizer.execute_query("""
                    UPDATE gmail_sync_jobs 
                    SET progress = 10, emails_synced = 0
                    WHERE job_id = ?
                """, (job_id,), fetch=False)
                logger.info(f"📊 Sync job {job_id} - {len(messages)} messages found, progress set to 10%")
            else:
                logger.warning(f"⚠️ Sync job {job_id} - No messages found")
            
            emails_synced = 0
            contacts_found = 0
            leads_identified = 0
            mailbox_automation_enabled = os.getenv("MAILBOX_AUTOMATION_ENABLED", "").lower() in {"1", "true", "yes"}
            actions = None
            if mailbox_automation_enabled:
                try:
                    from email_automation.actions import MinimalEmailActions
                    from email_automation.ai_assistant import MinimalAIEmailAssistant
                    actions = MinimalEmailActions(services={
                        "gmail": service,
                        "ai_assistant": MinimalAIEmailAssistant()
                    })
                except Exception as init_error:
                    logger.warning("Mailbox automation init failed: %s", init_error)
                    mailbox_automation_enabled = False
            
            for message in messages:
                try:
                    # Store email
                    email_id = self._store_email(user_id, message)
                    if email_id:
                        emails_synced += 1
                        try:
                            from email_automation.email_event_log import record_email_event

                            sid_rows = db_optimizer.execute_query(
                                "SELECT id FROM synced_emails WHERE user_id = ? AND gmail_id = ? LIMIT 1",
                                (user_id, message.get("id")),
                            )
                            sid = int(sid_rows[0]["id"]) if sid_rows else None
                            record_email_event(
                                user_id,
                                "email.received",
                                provider="gmail",
                                message_id=message.get("id"),
                                thread_id=message.get("threadId"),
                                synced_email_id=sid,
                                payload={"gmail_sync_job_id": job_id},
                                status="applied",
                                source="gmail_sync",
                            )
                        except Exception as ev_err:
                            logger.debug("email.received event skipped: %s", ev_err)

                        try:
                            owner_rows = db_optimizer.execute_query(
                                "SELECT email FROM users WHERE id = ? LIMIT 1", (user_id,)
                            )
                            owner_email = (
                                (owner_rows[0].get("email") or "").strip().lower()
                                if owner_rows
                                else None
                            ) or None
                        except Exception:
                            owner_email = None

                        # Unified: orchestrate_incoming always runs inbound capture + automations;
                        # classify/process runs only when MAILBOX_AUTOMATION_ENABLED.
                        try:
                            from email_automation.parser import MinimalEmailParser
                            from email_automation.pipeline import orchestrate_incoming
                            from core.request_correlation import get_or_create_correlation_id
                            from core.trace_context import get_trace_id

                            parsed_msg = MinimalEmailParser().parse_message(message)
                            corr_body = {
                                "message_id": message.get("id"),
                                "provider": "gmail",
                                "user_id": user_id,
                            }
                            correlation_id = get_or_create_correlation_id(
                                None, corr_body
                            )
                            trace_id = (
                                get_trace_id()
                                if mailbox_automation_enabled
                                and "core.trace_context" in sys.modules
                                else None
                            )
                            orchestrate_incoming(
                                parsed_msg,
                                user_id=user_id,
                                actions=actions if mailbox_automation_enabled and actions else None,
                                trace_id=trace_id,
                                correlation_id=correlation_id,
                                synced_email_row_id=sid,
                                external_message_id=str(message.get("id") or email_id or ""),
                                mailbox_owner_email=owner_email,
                                provider="gmail",
                                run_mailbox_ai=bool(
                                    mailbox_automation_enabled and actions
                                ),
                            )
                        except Exception as automation_error:
                            logger.warning(
                                "Inbound pipeline failed for message %s: %s",
                                message.get("id"),
                                automation_error,
                            )
                    
                    # Extract and store contacts
                    contacts = self._extract_contacts(message)
                    for contact in contacts:
                        if self._store_contact(user_id, contact):
                            contacts_found += 1
                    
                    # Calculate lead score
                    lead_score = self._calculate_lead_score(message, contacts)
                    if lead_score > 50:  # Threshold for lead identification
                        leads_identified += 1
                    
                    # Update progress in job table (after every email for real-time updates)
                    progress = int((emails_synced / len(messages)) * 100) if messages and len(messages) > 0 else 0
                    # Ensure progress is at least 10% after fetching messages, then increment
                    if progress < 10 and emails_synced > 0:
                        progress = 10 + int((emails_synced / len(messages)) * 90)  # 10-100% range
                    db_optimizer.execute_query("""
                        UPDATE gmail_sync_jobs 
                        SET progress = ?, emails_synced = ?
                        WHERE job_id = ?
                    """, (progress, emails_synced, job_id), fetch=False)
                    
                    # Update user_sync_status more frequently for real-time progress
                    # For small batches (< 20 emails), update after every email
                    # For larger batches, update every 3-5 emails
                    update_frequency = 1 if len(messages) < 20 else max(1, min(3, len(messages) // 10))
                    if emails_synced % update_frequency == 0 or emails_synced == len(messages) or emails_synced == 1:
                        try:
                            # Count total emails for this user
                            total_count_result = db_optimizer.execute_query(
                                "SELECT COUNT(*) as total FROM synced_emails WHERE user_id = ?",
                                (user_id,)
                            )
                            total_emails = total_count_result[0]['total'] if total_count_result and total_count_result[0] else emails_synced
                            
                            # Update status to show progress
                            db_optimizer.upsert_user_sync_status_merge(
                                user_id,
                                last_sync=_utcnow_naive().isoformat(),
                                sync_status="in_progress",
                                syncing=1,
                                total_emails=total_emails,
                            )
                        except Exception as status_update_error:
                            logger.warning(f"Could not update sync status during progress: {status_update_error}")
                    
                except Exception as e:
                    logger.warning(f"Failed to process email {message.get('id', 'unknown')}: {e}")
                    continue
            
            return {
                'emails_synced': emails_synced,
                'contacts_found': contacts_found,
                'leads_identified': leads_identified
            }
            
        except Exception as e:
            logger.error(f"❌ Email sync failed: {e}")
            raise
    
    def _get_gmail_messages(self, service) -> List[Dict[str, Any]]:
        """Get messages from Gmail API (paginates nextPageToken until cap or no more results)."""
        try:
            end_date = _utcnow_naive()
            start_date = end_date - timedelta(days=self.sync_days)
            query = f"after:{start_date.strftime('%Y/%m/%d')} before:{end_date.strftime('%Y/%m/%d')}"

            message_ids: List[str] = []
            page_token = None
            while len(message_ids) < self.sync_max_messages:
                page_size = min(self.sync_page_size, self.sync_max_messages - len(message_ids))
                list_params = {
                    'userId': 'me',
                    'q': query,
                    'maxResults': page_size,
                }
                if page_token:
                    list_params['pageToken'] = page_token
                results = service.users().messages().list(**list_params).execute()
                batch = results.get('messages', []) or []
                for m in batch:
                    if len(message_ids) >= self.sync_max_messages:
                        break
                    message_ids.append(m['id'])
                page_token = results.get('nextPageToken')
                if not page_token or not batch:
                    break

            full_messages: List[Dict[str, Any]] = []
            for mid in message_ids:
                try:
                    msg = service.users().messages().get(
                        userId='me',
                        id=mid,
                        format='full',
                    ).execute()
                    full_messages.append(msg)
                except Exception as e:
                    logger.warning(f"Failed to get message {mid}: {e}")
                    continue

            return full_messages

        except Exception as e:
            logger.error(f"❌ Gmail message retrieval failed: {e}")
            return []
    
    def _store_email(self, user_id: int, message: Dict[str, Any]) -> Optional[int]:
        """Store email in database"""
        try:
            # Extract message data
            headers = message.get('payload', {}).get('headers', [])
            header_dict = {h['name'].lower(): h['value'] for h in headers}
            
            subject = header_dict.get('subject', 'No Subject')
            sender = header_dict.get('from', '')
            recipient = header_dict.get('to', '')
            date_str = header_dict.get('date', '')
            
            # Parse date
            try:
                from email.utils import parsedate_to_datetime
                date = parsedate_to_datetime(date_str)
            except Exception as parse_error:
                logger.debug("Failed to parse email date '%s': %s", date_str, parse_error)
                date = _utcnow_naive()
            
            # Extract body and rewrite cid: inline images to /api/email/.../embedded-image/... (same as live Gmail fetch)
            body = self._extract_email_body(message.get('payload', {}))
            if body and '<' in body:
                try:
                    from core.gmail_inline_images import (
                        extract_embedded_image_map,
                        fix_legacy_embedded_image_api_paths,
                        rewrite_html_cid_to_proxy_urls,
                    )

                    emb = extract_embedded_image_map(message.get('payload', {}))
                    if emb:
                        body = rewrite_html_cid_to_proxy_urls(body, message['id'], emb)
                    body = fix_legacy_embedded_image_api_paths(body)
                except Exception as exc:
                    logger.debug("Inline image rewrite skipped: %s", exc)

            # Get labels
            labels = message.get('labelIds', [])
            # Align with Gmail: UNREAD label present => not read yet
            is_read = 0 if 'UNREAD' in labels else 1

            # Store in database
            db_optimizer.upsert_synced_email_from_gmail(
                user_id,
                message["id"],
                message.get("threadId"),
                subject,
                sender,
                recipient,
                date.isoformat(),
                body,
                json.dumps(labels),
                is_read,
            )

            return 1
            
        except Exception as e:
            logger.error(f"❌ Email storage failed: {e}")
            return None
    
    def _extract_email_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body from payload - prefers HTML, falls back to text"""
        try:
            body_text = ""
            body_html = ""
            
            def extract_from_part(part: Dict[str, Any]):
                """Recursively extract body from part"""
                nonlocal body_text, body_html
                mime_type = part.get('mimeType', '')
                
                if mime_type == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data and not body_text:  # Only use first text part
                        import base64
                        try:
                            body_text = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        except Exception as decode_error:
                            logger.debug("Failed to decode text/plain part: %s", decode_error)
                
                elif mime_type == 'text/html':
                    data = part.get('body', {}).get('data', '')
                    if data and not body_html:  # Only use first HTML part
                        import base64
                        try:
                            body_html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        except Exception as decode_error:
                            logger.debug("Failed to decode text/html part: %s", decode_error)
                
                # Recursively check nested parts
                if 'parts' in part:
                    for subpart in part['parts']:
                        extract_from_part(subpart)
            
            # Extract from payload
            if 'parts' in payload:
                # Multipart message - check all parts
                for part in payload['parts']:
                    extract_from_part(part)
            else:
                # Single part message
                extract_from_part(payload)
            
            # Prefer HTML for rich emails, fallback to text
            if body_html:
                return body_html
            elif body_text:
                return body_text
            else:
                return ""
            
        except Exception as e:
            logger.error(f"❌ Email body extraction failed: {e}")
            return ""
    
    def _extract_contacts(self, message: Dict[str, Any]) -> List[Contact]:
        """Extract contacts from email message"""
        try:
            contacts = []
            headers = message.get('payload', {}).get('headers', [])
            header_dict = {h['name'].lower(): h['value'] for h in headers}
            
            # Extract sender
            sender = header_dict.get('from', '')
            if sender:
                contact = self._parse_contact_string(sender)
                if contact:
                    contacts.append(contact)
            
            # Extract recipient
            recipient = header_dict.get('to', '')
            if recipient:
                contact = self._parse_contact_string(recipient)
                if contact:
                    contacts.append(contact)
            
            return contacts
            
        except Exception as e:
            logger.error(f"❌ Contact extraction failed: {e}")
            return []
    
    def _parse_contact_string(self, contact_str: str) -> Optional[Contact]:
        """Parse contact string into Contact object"""
        try:
            import re
            
            # Extract email
            email_match = re.search(r'<([^>]+)>', contact_str)
            if email_match:
                email = email_match.group(1)
            else:
                email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', contact_str)
                if email_match:
                    email = email_match.group(1)
                else:
                    return None
            
            # Extract name
            name = contact_str.replace(f'<{email}>', '').strip()
            if not name or name == email:
                name = email.split('@')[0]
            
            # Extract company from email domain
            company = email.split('@')[1].split('.')[0].title()
            
            return Contact(
                email=email,
                name=name,
                company=company,
                last_contact=_utcnow_naive(),
                contact_count=1,
                lead_score=0
            )
            
        except Exception as e:
            logger.error(f"❌ Contact parsing failed: {e}")
            return None
    
    def _store_contact(self, user_id: int, contact: Contact) -> bool:
        """Store contact in database"""
        try:
            # Check if contact already exists
            existing = db_optimizer.execute_query("""
                SELECT id, contact_count FROM contacts 
                WHERE user_id = ? AND email = ?
            """, (user_id, contact.email))
            
            if existing:
                # Update existing contact
                contact_id = existing[0]['id']
                new_count = existing[0]['contact_count'] + 1
                
                db_optimizer.execute_query("""
                    UPDATE contacts 
                    SET contact_count = ?, last_contact = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_count, contact.last_contact.isoformat(), contact_id), fetch=False)
            else:
                # Create new contact
                db_optimizer.execute_query("""
                    INSERT INTO contacts 
                    (user_id, email, name, company, last_contact, contact_count, lead_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    contact.email,
                    contact.name,
                    contact.company,
                    contact.last_contact.isoformat(),
                    contact.contact_count,
                    contact.lead_score
                ), fetch=False)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Contact storage failed: {e}")
            return False
    
    def _calculate_lead_score(self, message: Dict[str, Any], contacts: List[Contact]) -> int:
        """Calculate lead score for email message"""
        try:
            score = 0
            
            # Base score
            score += 10
            
            # Subject analysis
            headers = message.get('payload', {}).get('headers', [])
            header_dict = {h['name'].lower(): h['value'] for h in headers}
            subject = header_dict.get('subject', '').lower()
            
            # High-value keywords
            high_value_keywords = ['meeting', 'demo', 'proposal', 'contract', 'partnership', 'collaboration']
            for keyword in high_value_keywords:
                if keyword in subject:
                    score += 20
            
            # Business keywords
            business_keywords = ['business', 'company', 'enterprise', 'solution', 'service']
            for keyword in business_keywords:
                if keyword in subject:
                    score += 10
            
            # Contact analysis
            for contact in contacts:
                # Company domain analysis
                domain = contact.email.split('@')[1]
                if domain in ['gmail.com', 'yahoo.com', 'hotmail.com']:
                    score -= 5  # Personal email
                else:
                    score += 15  # Business email
            
            # Body analysis
            body = self._extract_email_body(message.get('payload', {}))
            if 'urgent' in body.lower():
                score += 15
            if 'asap' in body.lower():
                score += 10
            
            return min(max(score, 0), 100)  # Clamp between 0 and 100
            
        except Exception as e:
            logger.error(f"❌ Lead score calculation failed: {e}")
            return 0
    
    def get_sync_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get sync job status"""
        try:
            job_data = db_optimizer.execute_query("""
                SELECT id, user_id, job_id, status, progress, emails_synced, contacts_found, leads_identified, created_at, started_at, completed_at, error_message, metadata FROM gmail_sync_jobs WHERE job_id = ?
            """, (job_id,))
            
            if job_data:
                job = job_data[0]
                return {
                    'job_id': job['job_id'],
                    'status': job['status'],
                    'progress': job['progress'],
                    'emails_synced': job['emails_synced'],
                    'contacts_found': job['contacts_found'],
                    'leads_identified': job['leads_identified'],
                    'created_at': job['created_at'],
                    'started_at': job['started_at'],
                    'completed_at': job['completed_at'],
                    'error_message': job['error_message']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Sync job status retrieval failed: {e}")
            return None
    
    def get_user_sync_stats(self, user_id: int) -> Dict[str, Any]:
        """Get sync statistics for a user"""
        try:
            # Get total counts
            email_count = db_optimizer.execute_query("""
                SELECT COUNT(*) as count FROM synced_emails WHERE user_id = ?
            """, (user_id,))
            
            contact_count = db_optimizer.execute_query("""
                SELECT COUNT(*) as count FROM contacts WHERE user_id = ?
            """, (user_id,))
            
            lead_count = db_optimizer.execute_query("""
                SELECT COUNT(*) as count FROM contacts WHERE user_id = ? AND lead_score > 50
            """, (user_id,))
            
            # Get recent activity
            recent_pred = db_optimizer.sql_column_newer_than_n_days_ago("date", 7)
            recent_emails = db_optimizer.execute_query(f"""
                SELECT COUNT(*) as count FROM synced_emails 
                WHERE user_id = ? AND {recent_pred}
            """, (user_id,))
            
            return {
                'total_emails': email_count[0]['count'] if email_count else 0,
                'total_contacts': contact_count[0]['count'] if contact_count else 0,
                'total_leads': lead_count[0]['count'] if lead_count else 0,
                'recent_emails': recent_emails[0]['count'] if recent_emails else 0
            }
            
        except Exception as e:
            logger.error(f"❌ User sync stats retrieval failed: {e}")
            return {}

# Global Gmail sync job manager
gmail_sync_job_manager = GmailSyncJobManager()

# Task functions for Redis workers
def process_gmail_sync_job(job_id: str, **kwargs):
    """Process Gmail sync job task"""
    return gmail_sync_job_manager.process_sync_job(job_id)

def queue_gmail_sync_job(user_id: int, sync_type: str = 'full', metadata: Dict[str, Any] = None, **kwargs):
    """Queue Gmail sync job task"""
    return gmail_sync_job_manager.queue_sync_job(user_id, sync_type, metadata)
