#!/usr/bin/env python3
"""
Gmail Sync Background Jobs
Background processing for Gmail email synchronization with Redis queues
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
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
from core.google_oauth import google_oauth_manager

logger = logging.getLogger(__name__)

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
        self.sync_limit = int(os.getenv('GMAIL_SYNC_LIMIT', '100'))  # Max emails per sync
        self.sync_days = int(os.getenv('GMAIL_SYNC_DAYS', '30'))  # Days to sync
        self._connect_redis()
        self._initialize_tables()
    
    def _connect_redis(self):
        """Connect to Redis for job queues"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, Gmail sync jobs will be processed synchronously")
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
            logger.info("✅ Gmail sync Redis connection established")
            
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
            
            # Create synced emails table
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS synced_emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    gmail_id TEXT NOT NULL,
                    thread_id TEXT,
                    subject TEXT,
                    sender TEXT,
                    recipient TEXT,
                    date DATETIME,
                    body TEXT,
                    labels TEXT DEFAULT '[]',
                    attachments TEXT DEFAULT '[]',
                    processed BOOLEAN DEFAULT FALSE,
                    lead_score INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, gmail_id)
                )
            """, fetch=False)
            
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
            
            # Queue in Redis if available
            if self.redis_client:
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
    
    def process_sync_job(self, job_id: str) -> Dict[str, Any]:
        """Process a Gmail sync job"""
        try:
            # Get job details
            job_data = db_optimizer.execute_query("""
                SELECT * FROM gmail_sync_jobs WHERE job_id = ?
            """, (job_id,))
            
            if not job_data:
                return {
                    'success': False,
                    'error': 'Job not found',
                    'error_code': 'JOB_NOT_FOUND'
                }
            
            job = job_data[0]
            user_id = job['user_id']
            
            # Update job status
            db_optimizer.execute_query("""
                UPDATE gmail_sync_jobs 
                SET status = 'processing', started_at = datetime('now')
                WHERE job_id = ?
            """, (job_id,), fetch=False)
            
            # Get valid access token
            access_token = google_oauth_manager.get_valid_access_token(user_id)
            if not access_token:
                # Try to refresh token
                refresh_result = google_oauth_manager.refresh_access_token(user_id)
                if refresh_result['success']:
                    access_token = refresh_result['access_token']
                else:
                    raise Exception("Failed to get valid access token")
            
            # Initialize Gmail service
            if not GMAIL_API_AVAILABLE:
                raise Exception("Gmail API not available")
            
            credentials = Credentials(access_token)
            service = build('gmail', 'v1', credentials=credentials)
            
            # Sync emails
            sync_result = self._sync_emails(service, user_id, job_id)
            
            # Update job with results
            db_optimizer.execute_query("""
                UPDATE gmail_sync_jobs 
                SET status = 'completed', completed_at = datetime('now'),
                    progress = 100, emails_synced = ?, contacts_found = ?, leads_identified = ?
                WHERE job_id = ?
            """, (
                sync_result['emails_synced'],
                sync_result['contacts_found'],
                sync_result['leads_identified'],
                job_id
            ), fetch=False)
            
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
            except:
                pass
            
            return {
                'success': False,
                'error': str(e),
                'error_code': 'SYNC_PROCESSING_FAILED'
            }
    
    def _sync_emails(self, service, user_id: int, job_id: str) -> Dict[str, Any]:
        """Sync emails from Gmail"""
        try:
            # Get messages from Gmail
            messages = self._get_gmail_messages(service)
            
            emails_synced = 0
            contacts_found = 0
            leads_identified = 0
            
            for message in messages:
                try:
                    # Store email
                    email_id = self._store_email(user_id, message)
                    if email_id:
                        emails_synced += 1
                    
                    # Extract and store contacts
                    contacts = self._extract_contacts(message)
                    for contact in contacts:
                        if self._store_contact(user_id, contact):
                            contacts_found += 1
                    
                    # Calculate lead score
                    lead_score = self._calculate_lead_score(message, contacts)
                    if lead_score > 50:  # Threshold for lead identification
                        leads_identified += 1
                    
                    # Update progress
                    progress = int((emails_synced / len(messages)) * 100)
                    db_optimizer.execute_query("""
                        UPDATE gmail_sync_jobs 
                        SET progress = ?, emails_synced = ?
                        WHERE job_id = ?
                    """, (progress, emails_synced, job_id), fetch=False)
                    
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
        """Get messages from Gmail API"""
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=self.sync_days)
            
            # Build query
            query = f"after:{start_date.strftime('%Y/%m/%d')} before:{end_date.strftime('%Y/%m/%d')}"
            
            # Get message list
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=self.sync_limit
            ).execute()
            
            messages = results.get('messages', [])
            
            # Get full message details
            full_messages = []
            for message in messages:
                try:
                    msg = service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()
                    full_messages.append(msg)
                except Exception as e:
                    logger.warning(f"Failed to get message {message['id']}: {e}")
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
            except:
                date = datetime.utcnow()
            
            # Extract body
            body = self._extract_email_body(message.get('payload', {}))
            
            # Get labels
            labels = message.get('labelIds', [])
            
            # Store in database
            email_id = db_optimizer.execute_query("""
                INSERT OR REPLACE INTO synced_emails 
                (user_id, gmail_id, thread_id, subject, sender, recipient, date, body, labels)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                message['id'],
                message.get('threadId'),
                subject,
                sender,
                recipient,
                date.isoformat(),
                body,
                json.dumps(labels)
            ), fetch=False)
            
            return email_id
            
        except Exception as e:
            logger.error(f"❌ Email storage failed: {e}")
            return None
    
    def _extract_email_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body from payload"""
        try:
            body = ""
            
            if 'parts' in payload:
                # Multipart message
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            import base64
                            body = base64.urlsafe_b64decode(data).decode('utf-8')
                            break
            else:
                # Single part message
                if payload['mimeType'] == 'text/plain':
                    data = payload['body'].get('data', '')
                    if data:
                        import base64
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
            
            return body[:1000]  # Limit body length
            
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
                last_contact=datetime.utcnow(),
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
                    SET contact_count = ?, last_contact = ?, updated_at = datetime('now')
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
                SELECT * FROM gmail_sync_jobs WHERE job_id = ?
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
            recent_emails = db_optimizer.execute_query("""
                SELECT COUNT(*) as count FROM synced_emails 
                WHERE user_id = ? AND date > datetime('now', '-7 days')
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
