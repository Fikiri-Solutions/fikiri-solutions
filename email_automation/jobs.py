#!/usr/bin/env python3
"""
Email Job System for Background Processing
Welcome emails, notifications, and other email tasks via Redis queues
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Optional Redis integration
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.base import MIMEBase
    from email import encoders
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

def _is_test_mode() -> bool:
    return (
        os.getenv("FIKIRI_TEST_MODE") == "1"
        or os.getenv("FLASK_ENV") == "test"
        or bool(os.getenv("PYTEST_CURRENT_TEST"))
    )


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

@dataclass
class EmailJob:
    """Email job data structure"""
    id: str
    type: str
    recipient: str
    subject: str
    template: str
    data: Dict[str, Any]
    priority: int = 1
    created_at: float = None
    scheduled_at: float = None
    attempts: int = 0
    max_attempts: int = 3

class EmailJobManager:
    """Email job management system with Redis queues"""
    
    def __init__(self):
        self.redis_client = None
        self.queue_name = "fikiri:email:jobs"
        self.failed_queue_name = "fikiri:email:failed"
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('FROM_EMAIL', 'noreply@fikirisolutions.com')
        self.from_name = os.getenv('FROM_NAME', 'Fikiri Solutions')
        self._connect_redis()
        self._initialize_tables()
    
    def _connect_redis(self):
        """Connect to Redis for job queues"""
        if _is_test_mode():
            self.redis_client = None
            return
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, email jobs will be processed synchronously")
            return
        
        try:
            from core.redis_connection_helper import get_redis_client
            self.redis_client = get_redis_client(decode_responses=True, db=0)
            if self.redis_client:
                logger.info("✅ Email job Redis connection established")
            else:
                logger.warning("⚠️ Redis connection failed, email jobs will be processed synchronously")
        except Exception as e:
            logger.error(f"❌ Email job Redis connection failed: {e}")
            self.redis_client = None
    
    def _initialize_tables(self):
        """Initialize database tables for email job tracking"""
        try:
            # Create email jobs table
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS email_jobs (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    template TEXT,
                    data TEXT DEFAULT '{}',
                    priority INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    scheduled_at DATETIME,
                    sent_at DATETIME,
                    attempts INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 3,
                    error_message TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """, fetch=False)
            
            # Create indexes
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_email_jobs_status 
                ON email_jobs (status)
            """, fetch=False)
            
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_email_jobs_recipient 
                ON email_jobs (recipient)
            """, fetch=False)
            
            logger.info("✅ Email job tables initialized")
            
        except Exception as e:
            logger.error(f"❌ Email job table initialization failed: {e}")
    
    def queue_welcome_email(self, user_id: int, email: str, name: str, 
                           company_name: str = None) -> str:
        """Queue a welcome email for new users"""
        try:
            job_id = f"welcome_{user_id}_{int(time.time())}"
            
            email_data = {
                'user_id': user_id,
                'name': name,
                'email': email,
                'company_name': company_name or 'Your Company',
                'signup_date': _utcnow_naive().isoformat(),
                'dashboard_url': 'https://fikirisolutions.com/dashboard',
                'support_email': 'support@fikirisolutions.com'
            }
            
            job = EmailJob(
                id=job_id,
                type='welcome',
                recipient=email,
                subject=f'Welcome to Fikiri Solutions, {name}!',
                template='welcome',
                data=email_data,
                priority=1
            )
            
            return self._queue_job(job)
            
        except Exception as e:
            logger.error(f"❌ Welcome email queuing failed: {e}")
            return None
    
    def queue_onboarding_email(self, user_id: int, email: str, name: str, 
                              step: int, company_name: str = None) -> str:
        """Queue an onboarding progress email"""
        try:
            job_id = f"onboarding_{user_id}_{step}_{int(time.time())}"
            
            email_data = {
                'user_id': user_id,
                'name': name,
                'email': email,
                'step': step,
                'company_name': company_name or 'Your Company',
                'next_step_url': f'https://fikirisolutions.com/onboarding/{step + 1}',
                'dashboard_url': 'https://fikirisolutions.com/dashboard'
            }
            
            job = EmailJob(
                id=job_id,
                type='onboarding',
                recipient=email,
                subject=f'Onboarding Step {step} - Fikiri Solutions',
                template='onboarding',
                data=email_data,
                priority=2
            )
            
            return self._queue_job(job)
            
        except Exception as e:
            logger.error(f"❌ Onboarding email queuing failed: {e}")
            return None
    
    def queue_password_reset_email(self, email: str, reset_token: str, 
                                  name: str = None) -> str:
        """Queue a password reset email"""
        try:
            job_id = f"reset_{hash(email)}_{int(time.time())}"
            
            email_data = {
                'email': email,
                'name': name or 'User',
                'reset_token': reset_token,
                'reset_url': f'https://fikirisolutions.com/reset-password?token={reset_token}',
                'expires_in': '1 hour'
            }
            
            job = EmailJob(
                id=job_id,
                type='password_reset',
                recipient=email,
                subject='Reset Your Fikiri Solutions Password',
                template='password_reset',
                data=email_data,
                priority=1
            )
            
            return self._queue_job(job)
            
        except Exception as e:
            logger.error(f"❌ Password reset email queuing failed: {e}")
            return None
    
    def queue_notification_email(self, user_id: int, email: str, subject: str, 
                                message: str, notification_type: str = 'general') -> str:
        """Queue a notification email"""
        try:
            job_id = f"notification_{user_id}_{int(time.time())}"
            
            email_data = {
                'user_id': user_id,
                'email': email,
                'subject': subject,
                'message': message,
                'notification_type': notification_type,
                'dashboard_url': 'https://fikirisolutions.com/dashboard'
            }
            
            job = EmailJob(
                id=job_id,
                type='notification',
                recipient=email,
                subject=subject,
                template='notification',
                data=email_data,
                priority=3
            )
            
            return self._queue_job(job)
            
        except Exception as e:
            logger.error(f"❌ Notification email queuing failed: {e}")
            return None
    
    def _queue_job(self, job: EmailJob) -> str:
        """Queue an email job"""
        try:
            # Set timestamps
            if not job.created_at:
                job.created_at = time.time()
            if not job.scheduled_at:
                job.scheduled_at = job.created_at
            
            # Store in database
            db_optimizer.execute_query("""
                INSERT INTO email_jobs 
                (id, type, recipient, subject, template, data, priority, scheduled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id,
                job.type,
                job.recipient,
                job.subject,
                job.template,
                json.dumps(job.data),
                job.priority,
                datetime.fromtimestamp(job.scheduled_at).isoformat()
            ), fetch=False)
            
            # Queue in Redis if available
            if self.redis_client:
                job_data = {
                    'id': job.id,
                    'type': job.type,
                    'recipient': job.recipient,
                    'subject': job.subject,
                    'template': job.template,
                    'data': job.data,
                    'priority': job.priority,
                    'created_at': job.created_at,
                    'scheduled_at': job.scheduled_at,
                    'attempts': job.attempts,
                    'max_attempts': job.max_attempts
                }
                
                # Add to priority queue
                self.redis_client.zadd(
                    f"{self.queue_name}:scheduled",
                    {json.dumps(job_data): job.scheduled_at}
                )
            
            logger.info(f"✅ Queued email job: {job.id} ({job.type})")
            return job.id
            
        except Exception as e:
            logger.error(f"❌ Email job queuing failed: {e}")
            return None
    
    def process_jobs(self, max_jobs: int = 10) -> int:
        """Process pending email jobs"""
        if not EMAIL_AVAILABLE:
            logger.warning("Email functionality not available")
            return 0
        
        processed = 0
        
        try:
            # Get pending jobs from database (rulepack compliance: specific columns, not SELECT *)
            jobs = db_optimizer.execute_query("""
                SELECT id, type, recipient, subject, template, data, priority, status, created_at, scheduled_at, sent_at, attempts, max_attempts, error_message, metadata 
                FROM email_jobs 
                WHERE status = 'pending' 
                AND (scheduled_at IS NULL OR scheduled_at <= datetime('now'))
                ORDER BY priority ASC, created_at ASC
                LIMIT ?
            """, (max_jobs,))
            
            for job_record in jobs:
                try:
                    # Process the job
                    success = self._process_single_job(job_record)
                    
                    if success:
                        # Mark as sent
                        db_optimizer.execute_query("""
                            UPDATE email_jobs 
                            SET status = 'sent', sent_at = datetime('now')
                            WHERE id = ?
                        """, (job_record['id'],), fetch=False)
                        
                        processed += 1
                        logger.info(f"✅ Sent email: {job_record['id']}")
                    else:
                        # Increment attempts
                        attempts = job_record['attempts'] + 1
                        max_attempts = job_record['max_attempts']
                        
                        if attempts >= max_attempts:
                            # Mark as failed
                            db_optimizer.execute_query("""
                                UPDATE email_jobs 
                                SET status = 'failed', attempts = ?
                                WHERE id = ?
                            """, (attempts, job_record['id']), fetch=False)
                            
                            logger.error(f"❌ Email job failed permanently: {job_record['id']}")
                        else:
                            # Schedule retry
                            retry_delay = min(300 * (2 ** attempts), 3600)  # Exponential backoff, max 1 hour
                            retry_time = _utcnow_naive() + timedelta(seconds=retry_delay)
                            
                            db_optimizer.execute_query("""
                                UPDATE email_jobs 
                                SET attempts = ?, scheduled_at = ?
                                WHERE id = ?
                            """, (attempts, retry_time.isoformat(), job_record['id']), fetch=False)
                            
                            logger.warning(f"⚠️ Email job retry scheduled: {job_record['id']} (attempt {attempts})")
                
                except Exception as e:
                    logger.error(f"❌ Error processing email job {job_record['id']}: {e}")
                    continue
            
            return processed
            
        except Exception as e:
            logger.error(f"❌ Email job processing failed: {e}")
            return processed
    
    def _process_single_job(self, job_record: Dict[str, Any]) -> bool:
        """Process a single email job"""
        try:
            # Parse job data
            data = json.loads(job_record.get('data', '{}'))
            template = job_record.get('template', 'default')
            
            # Generate email content
            content = self._generate_email_content(template, data)
            
            # Send email
            return self._send_email(
                to_email=job_record['recipient'],
                subject=job_record['subject'],
                content=content
            )
            
        except Exception as e:
            logger.error(f"❌ Single email job processing failed: {e}")
            return False
    
    def _generate_email_content(self, template: str, data: Dict[str, Any]) -> str:
        """Generate email content based on template"""
        try:
            if template == 'welcome':
                return self._generate_welcome_email(data)
            elif template == 'onboarding':
                return self._generate_onboarding_email(data)
            elif template == 'password_reset':
                return self._generate_password_reset_email(data)
            elif template == 'notification':
                return self._generate_notification_email(data)
            else:
                return self._generate_default_email(data)
                
        except Exception as e:
            logger.error(f"❌ Email content generation failed: {e}")
            return "Email content generation failed."
    
    def _generate_welcome_email(self, data: Dict[str, Any]) -> str:
        """Generate welcome email content"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2563eb;">Welcome to Fikiri Solutions, {data.get('name', 'there')}!</h1>
                
                <p>Thank you for joining Fikiri Solutions! We're excited to help you streamline your business operations with our AI-powered tools.</p>
                
                <p>Your account has been successfully created for <strong>{data.get('company_name', 'Your Company')}</strong>.</p>
                
                <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0;">What's next?</h3>
                    <ul>
                        <li>Complete your onboarding to connect your Gmail</li>
                        <li>Set up your first automation workflows</li>
                        <li>Start syncing your contacts and leads</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{data.get('dashboard_url', 'https://fikirisolutions.com/dashboard')}" 
                       style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                        Get Started
                    </a>
                </div>
                
                <p>If you have any questions, feel free to reach out to our support team at <a href="mailto:{data.get('support_email', 'support@fikirisolutions.com')}">{data.get('support_email', 'support@fikirisolutions.com')}</a>.</p>
                
                <p>Best regards,<br>The Fikiri Solutions Team</p>
            </div>
        </body>
        </html>
        """
    
    def _generate_onboarding_email(self, data: Dict[str, Any]) -> str:
        """Generate onboarding email content"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2563eb;">Onboarding Progress - Step {data.get('step', 1)}</h1>
                
                <p>Hi {data.get('name', 'there')},</p>
                
                <p>Great progress on your Fikiri Solutions setup! You've completed step {data.get('step', 1)} of your onboarding.</p>
                
                <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0;">Next Steps:</h3>
                    <p>Continue your onboarding to unlock the full power of Fikiri Solutions.</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{data.get('next_step_url', 'https://fikirisolutions.com/onboarding')}" 
                       style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                        Continue Onboarding
                    </a>
                </div>
                
                <p>Best regards,<br>The Fikiri Solutions Team</p>
            </div>
        </body>
        </html>
        """
    
    def _generate_password_reset_email(self, data: Dict[str, Any]) -> str:
        """Generate password reset email content"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2563eb;">Reset Your Password</h1>
                
                <p>Hi {data.get('name', 'there')},</p>
                
                <p>We received a request to reset your password for your Fikiri Solutions account.</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{data.get('reset_url', '#')}" 
                       style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                
                <p><strong>This link will expire in {data.get('expires_in', '1 hour')}.</strong></p>
                
                <p>If you didn't request this password reset, please ignore this email. Your password will remain unchanged.</p>
                
                <p>Best regards,<br>The Fikiri Solutions Team</p>
            </div>
        </body>
        </html>
        """
    
    def _generate_notification_email(self, data: Dict[str, Any]) -> str:
        """Generate notification email content"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2563eb;">{data.get('subject', 'Notification')}</h1>
                
                <p>Hi {data.get('name', 'there')},</p>
                
                <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    {data.get('message', 'You have a new notification.')}
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{data.get('dashboard_url', 'https://fikirisolutions.com/dashboard')}" 
                       style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                        View Dashboard
                    </a>
                </div>
                
                <p>Best regards,<br>The Fikiri Solutions Team</p>
            </div>
        </body>
        </html>
        """
    
    def _generate_default_email(self, data: Dict[str, Any]) -> str:
        """Generate default email content"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2563eb;">Fikiri Solutions</h1>
                <p>Hello,</p>
                <p>You have a new message from Fikiri Solutions.</p>
                <p>Best regards,<br>The Fikiri Solutions Team</p>
            </div>
        </body>
        </html>
        """
    
    def _send_email(self, to_email: str, subject: str, content: str) -> bool:
        """Send email via SMTP"""
        try:
            if not self.smtp_username or not self.smtp_password:
                logger.warning("SMTP credentials not configured")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add HTML content
            html_part = MIMEText(content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Email sending failed: {e}")
            return False
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get email job status"""
        try:
            # Rulepack compliance: specific columns, not SELECT *
            job_data = db_optimizer.execute_query("""
                SELECT id, type, recipient, subject, template, data, priority, status, created_at, scheduled_at, sent_at, attempts, max_attempts, error_message, metadata FROM email_jobs WHERE id = ?
            """, (job_id,))
            
            if job_data:
                job = job_data[0]
                return {
                    'id': job['id'],
                    'type': job['type'],
                    'recipient': job['recipient'],
                    'status': job['status'],
                    'created_at': job['created_at'],
                    'sent_at': job['sent_at'],
                    'attempts': job['attempts'],
                    'error_message': job['error_message']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Job status retrieval failed: {e}")
            return None
    
    def cleanup_old_jobs(self, days: int = 30):
        """Clean up old email jobs"""
        try:
            cutoff_date = _utcnow_naive() - timedelta(days=days)
            
            db_optimizer.execute_query("""
                DELETE FROM email_jobs 
                WHERE created_at < ? AND status IN ('sent', 'failed')
            """, (cutoff_date.isoformat(),), fetch=False)
            
            logger.info(f"✅ Cleaned up email jobs older than {days} days")
            
        except Exception as e:
            logger.error(f"❌ Email job cleanup failed: {e}")

# Global email job manager
email_job_manager = EmailJobManager()

# Task functions for Redis workers
def send_welcome_email(user_id: int, email: str, name: str, company_name: str = None, **kwargs):
    """Send welcome email task"""
    return email_job_manager.queue_welcome_email(user_id, email, name, company_name)

def send_onboarding_email(user_id: int, email: str, name: str, step: int, company_name: str = None, **kwargs):
    """Send onboarding email task"""
    return email_job_manager.queue_onboarding_email(user_id, email, name, step, company_name)

def send_password_reset_email(email: str, reset_token: str, name: str = None, **kwargs):
    """Send password reset email task"""
    return email_job_manager.queue_password_reset_email(email, reset_token, name)

def send_notification_email(user_id: int, email: str, subject: str, message: str, notification_type: str = 'general', **kwargs):
    """Send notification email task"""
    return email_job_manager.queue_notification_email(user_id, email, subject, message, notification_type)
