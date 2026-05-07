#!/usr/bin/env python3
"""
Email Job System for Background Processing
Welcome emails, notifications, and other email tasks via Redis queues
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from config import config as app_config
from core.email_branding import wrap_html_email_body

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

# IANA example.{com,net,org} publish Null MX — SMTP accept + DSN bounce to FROM.
# RFC 2606: *.test / *.invalid are reserved; do not attempt real delivery.
_RESERVED_IANA_EXAMPLE_DOMAINS = frozenset({"example.com", "example.net", "example.org"})


def _should_skip_smtp_delivery(to_email: str) -> bool:
    if not to_email or "@" not in to_email:
        return False
    domain = to_email.rsplit("@", 1)[-1].strip().lower()
    if domain in _RESERVED_IANA_EXAMPLE_DOMAINS:
        return True
    if domain.endswith(".test") or domain.endswith(".invalid"):
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
        self.smtp_host = (
            os.getenv('SMTP_HOST')
            or os.getenv('SMTP_SERVER')
            or 'smtp.gmail.com'
        )
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_username = (os.getenv('SMTP_USERNAME') or '').strip() or None
        _raw_pw = os.getenv('SMTP_PASSWORD') or ''
        # Google shows app passwords as four groups; SMTP expects the 16 chars without spaces.
        self.smtp_password = _raw_pw.replace(' ', '').strip() or None
        self.from_email = os.getenv('FROM_EMAIL') or os.getenv(
            'EMAIL_FROM_ADDRESS', 'noreply@fikirisolutions.com'
        )
        self.from_name = os.getenv('FROM_NAME') or os.getenv('EMAIL_FROM_NAME', 'Fikiri Solutions')
        self._process_jobs_lock = threading.Lock()
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

    def _schedule_process_job(self, job_id: str) -> None:
        """
        Send only the job that was just queued. A bulk flush would process every old pending row
        (e.g. stale welcome emails) and spam SMTP on each resend.
        """
        if _is_test_mode():
            return

        def _run():
            with self._process_jobs_lock:
                try:
                    sent = self.process_job_by_id(job_id)
                    if sent:
                        logger.info("Email job sent: %s", job_id)
                except Exception as exc:
                    logger.error("Email job processing failed for %s: %s", job_id, exc, exc_info=True)

        thread = threading.Thread(target=_run, daemon=True, name="email-job-send")
        thread.start()

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
                'support_email': 'info@fikirisolutions.com'
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

    def queue_email_verification_email(
        self,
        user_id: int,
        email: str,
        name: str,
        verification_token: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        """Queue an email verification email"""
        try:
            job_id = f"verify_{user_id}_{int(time.time())}"
            verification_url = f"{app_config.get_frontend_url()}/verify-email?token={verification_token}"

            email_data = {
                'user_id': user_id,
                'email': email,
                'name': name or 'User',
                'verification_url': verification_url,
                'expires_in': '1 hour' if expires_in_seconds else None,
            }

            job = EmailJob(
                id=job_id,
                type='email_verification',
                recipient=email,
                subject='Verify Your Email - Fikiri Solutions',
                template='email_verification',
                data=email_data,
                priority=1,
            )

            return self._queue_job(job)

        except Exception as e:
            logger.error(f"❌ Email verification email queuing failed: {e}")
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
            self._schedule_process_job(job.id)
            return job.id
            
        except Exception as e:
            logger.error(f"❌ Email job queuing failed: {e}")
            return None
    
    def _try_send_job(self, job_record: Dict[str, Any]) -> Tuple[bool, bool, Optional[str]]:
        """
        Build content and send. Returns (success, allow_retry, error_message).
        allow_retry=False for missing SMTP config or SMTP auth errors (retries won't help).
        """
        try:
            data = json.loads(job_record.get('data', '{}'))
            template = job_record.get('template', 'default')
            content = self._generate_email_content(template, data)
            return self._send_email(
                to_email=job_record['recipient'],
                subject=job_record['subject'],
                content=content,
            )
        except Exception as e:
            logger.error("❌ Single email job processing failed: %s", e)
            return False, True, str(e)[:500]

    def _record_job_send_outcome(
        self,
        job_record: Dict[str, Any],
        success: bool,
        allow_retry: bool,
        error_message: Optional[str] = None,
    ) -> None:
        job_id = job_record['id']
        if success:
            db_optimizer.execute_query(
                """
                UPDATE email_jobs
                SET status = 'sent', sent_at = datetime('now'), error_message = NULL
                WHERE id = ?
                """,
                (job_id,),
                fetch=False,
            )
            recipient = (job_record.get("recipient") or "").strip()
            if _should_skip_smtp_delivery(recipient):
                logger.info(
                    "Email job closed without SMTP (reserved/non-deliverable recipient): %s → %s",
                    job_id,
                    recipient,
                )
            else:
                logger.info("✅ Sent email: %s", job_id)
            return

        attempts = int(job_record.get('attempts') or 0) + 1
        max_attempts = int(job_record.get('max_attempts') or 3)

        if not allow_retry or attempts >= max_attempts:
            db_optimizer.execute_query(
                """
                UPDATE email_jobs
                SET status = 'failed', attempts = ?, error_message = ?
                WHERE id = ?
                """,
                (attempts, error_message or 'send_failed', job_id),
                fetch=False,
            )
            logger.error("❌ Email job failed permanently: %s", job_id)
            return

        retry_delay = min(300 * (2 ** attempts), 3600)
        retry_time = _utcnow_naive() + timedelta(seconds=retry_delay)
        db_optimizer.execute_query(
            """
            UPDATE email_jobs
            SET attempts = ?, scheduled_at = ?, error_message = ?
            WHERE id = ?
            """,
            (attempts, retry_time.isoformat(), error_message, job_id),
            fetch=False,
        )
        logger.warning("⚠️ Email job retry scheduled: %s (attempt %s)", job_id, attempts)

    def process_job_by_id(self, job_id: str) -> int:
        """Process one pending job by id. Returns 1 if sent successfully, else 0."""
        if not EMAIL_AVAILABLE:
            logger.warning("Email functionality not available")
            return 0
        rows = db_optimizer.execute_query(
            """
            SELECT id, type, recipient, subject, template, data, priority, status, created_at, scheduled_at, sent_at, attempts, max_attempts, error_message, metadata
            FROM email_jobs
            WHERE id = ?
            AND status = 'pending'
            AND (
                scheduled_at IS NULL
                OR datetime(scheduled_at) <= datetime('now')
            )
            """,
            (job_id,),
        )
        if not rows:
            hint = db_optimizer.execute_query(
                "SELECT status, scheduled_at FROM email_jobs WHERE id = ?",
                (job_id,),
            )
            if not hint:
                logger.warning("Email job %s: no row in email_jobs", job_id)
            else:
                h = dict(hint[0]) if hasattr(hint[0], "keys") else hint[0]
                logger.warning(
                    "Email job %s: send skipped (status=%s scheduled_at=%s)",
                    job_id,
                    h.get("status"),
                    h.get("scheduled_at"),
                )
            return 0
        job_record = rows[0]
        try:
            success, allow_retry, err = self._try_send_job(job_record)
            self._record_job_send_outcome(job_record, success, allow_retry, err)
            return 1 if success else 0
        except Exception as e:
            logger.error("❌ Error processing email job %s: %s", job_id, e)
            return 0

    def process_jobs(self, max_jobs: int = 10) -> int:
        """Process pending email jobs (batch; use process_job_by_id from HTTP-triggered sends)."""
        if not EMAIL_AVAILABLE:
            logger.warning("Email functionality not available")
            return 0

        processed = 0

        try:
            jobs = db_optimizer.execute_query(
                """
                SELECT id, type, recipient, subject, template, data, priority, status, created_at, scheduled_at, sent_at, attempts, max_attempts, error_message, metadata
                FROM email_jobs
                WHERE status = 'pending'
                AND (
                    scheduled_at IS NULL
                    OR datetime(scheduled_at) <= datetime('now')
                )
                ORDER BY priority ASC, created_at ASC
                LIMIT ?
                """,
                (max_jobs,),
            )

            for job_record in jobs:
                try:
                    success, allow_retry, err = self._try_send_job(job_record)
                    self._record_job_send_outcome(job_record, success, allow_retry, err)
                    if success:
                        processed += 1
                except Exception as e:
                    logger.error("❌ Error processing email job %s: %s", job_record['id'], e)
                    continue

            return processed

        except Exception as e:
            logger.error("❌ Email job processing failed: %s", e)
            return processed
    
    def _generate_email_content(self, template: str, data: Dict[str, Any]) -> str:
        """Generate email content based on template"""
        try:
            if template == 'welcome':
                return self._generate_welcome_email(data)
            elif template == 'onboarding':
                return self._generate_onboarding_email(data)
            elif template == 'password_reset':
                return self._generate_password_reset_email(data)
            elif template == 'email_verification':
                return self._generate_email_verification_email(data)
            elif template == 'notification':
                return self._generate_notification_email(data)
            else:
                return self._generate_default_email(data)
                
        except Exception as e:
            logger.error(f"❌ Email content generation failed: {e}")
            return "Email content generation failed."
    
    def _generate_welcome_email(self, data: Dict[str, Any]) -> str:
        """Generate welcome email content"""
        inner = f"""
                <h1 style="color: #2563eb; font-size: 22px; margin-top: 0;">Welcome to Fikiri Solutions, {data.get('name', 'there')}!</h1>

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

                <p>If you have any questions, feel free to reach out to our support team at <a href="mailto:{data.get('support_email', 'info@fikirisolutions.com')}">{data.get('support_email', 'info@fikirisolutions.com')}</a>.</p>

                <p>Best regards,<br>The Fikiri Solutions Team</p>
        """
        return wrap_html_email_body(inner)
    
    def _generate_onboarding_email(self, data: Dict[str, Any]) -> str:
        """Generate onboarding email content"""
        inner = f"""
                <h1 style="color: #2563eb; font-size: 22px; margin-top: 0;">Onboarding Progress - Step {data.get('step', 1)}</h1>

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
        """
        return wrap_html_email_body(inner)
    
    def _generate_password_reset_email(self, data: Dict[str, Any]) -> str:
        """Generate password reset email content"""
        inner = f"""
                <h1 style="color: #2563eb; font-size: 22px; margin-top: 0;">Reset Your Password</h1>

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
        """
        return wrap_html_email_body(inner)

    def _generate_email_verification_email(self, data: Dict[str, Any]) -> str:
        """Generate email verification email content"""
        inner = f"""
                <h1 style="color: #2563eb; font-size: 22px; margin-top: 0;">Verify Your Email</h1>

                <p>Hi {data.get('name', 'there')},</p>

                <p>Thanks for signing up for Fikiri Solutions. Please verify your email address to activate your account.</p>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{data.get('verification_url', '#')}"
                       style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                        Verify Email
                    </a>
                </div>

                <p><strong>This link expires in {data.get('expires_in', '1 hour')}.</strong></p>

                <p>If you didn't create this account, you can safely ignore this email.</p>

                <p>Best regards,<br>The Fikiri Solutions Team</p>
        """
        return wrap_html_email_body(inner)
    
    def _generate_notification_email(self, data: Dict[str, Any]) -> str:
        """Generate notification email content"""
        inner = f"""
                <h1 style="color: #2563eb; font-size: 22px; margin-top: 0;">{data.get('subject', 'Notification')}</h1>

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
        """
        return wrap_html_email_body(inner)
    
    def _generate_default_email(self, data: Dict[str, Any]) -> str:
        """Generate default email content"""
        inner = """
                <h1 style="color: #2563eb; font-size: 22px; margin-top: 0;">Fikiri Solutions</h1>
                <p>Hello,</p>
                <p>You have a new message from Fikiri Solutions.</p>
                <p>Best regards,<br>The Fikiri Solutions Team</p>
        """
        return wrap_html_email_body(inner)
    
    def _send_email(self, to_email: str, subject: str, content: str) -> Tuple[bool, bool, Optional[str]]:
        """
        Send email via SMTP.
        Returns (success, allow_retry, error_message).
        """
        try:
            if _should_skip_smtp_delivery(to_email):
                logger.info("Skipping SMTP to non-deliverable/placeholder address: %s", to_email)
                return True, False, None

            if not self.smtp_username or not self.smtp_password:
                logger.warning("SMTP credentials not configured")
                return False, False, "smtp_not_configured"

            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject

            html_part = MIMEText(content, 'html')
            msg.attach(html_part)

            smtp_timeout = int(os.getenv("SMTP_TIMEOUT_SECONDS", "45"))
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=smtp_timeout) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            return True, True, None

        except smtplib.SMTPAuthenticationError as e:
            logger.error(
                "❌ SMTP authentication failed (535): use a valid SMTP user/password. "
                "For Gmail, use an App Password and SMTP_USERNAME=full email: %s",
                e,
            )
            return False, False, "smtp_authentication_failed"
        except Exception as e:
            logger.error("❌ Email sending failed: %s", e)
            return False, True, str(e)[:500]
    
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
