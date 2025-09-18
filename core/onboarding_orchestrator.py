"""
Backend Orchestration for First Sync
Handles the complete onboarding flow with background jobs and data seeding
"""

import json
import logging
import threading
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from core.database_optimization import db_optimizer
from core.enhanced_crm_service import enhanced_crm_service
from core.email_parser_service import email_parser_service
from core.automation_engine import automation_engine
from core.gmail_oauth import gmail_oauth_manager, gmail_sync_manager

logger = logging.getLogger(__name__)

@dataclass
class OnboardingJob:
    """Onboarding job data structure"""
    id: int
    user_id: int
    status: str  # 'pending', 'running', 'completed', 'failed'
    current_step: str
    progress: int  # 0-100
    started_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    metadata: Dict[str, Any]

class OnboardingOrchestrator:
    """Orchestrates the complete onboarding flow with background jobs"""
    
    def __init__(self):
        self.active_jobs: Dict[int, OnboardingJob] = {}
        self.job_lock = threading.Lock()
    
    def start_onboarding_job(self, user_id: int) -> Dict[str, Any]:
        """Start the complete onboarding process"""
        try:
            # Check if user already has an active job
            existing_job = self.get_user_job(user_id)
            if existing_job and existing_job.status in ['pending', 'running']:
                return {
                    'success': True,
                    'job_id': existing_job.id,
                    'message': 'Onboarding job already in progress'
                }
            
            # Create new onboarding job
            job_id = db_optimizer.execute_query(
                """INSERT INTO onboarding_jobs 
                   (user_id, status, current_step, progress, started_at, metadata) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, 'pending', 'initializing', 0, datetime.now().isoformat(), 
                 json.dumps({'steps': ['gmail_sync', 'lead_extraction', 'starter_automations', 'dashboard_seeding']})),
                fetch=False
            )
            
            # Start background job
            job_thread = threading.Thread(
                target=self._run_onboarding_job,
                args=(job_id, user_id),
                daemon=True
            )
            job_thread.start()
            
            logger.info(f"Started onboarding job {job_id} for user {user_id}")
            
            return {
                'success': True,
                'job_id': job_id,
                'message': 'Onboarding job started successfully'
            }
            
        except Exception as e:
            logger.error(f"Error starting onboarding job: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'ONBOARDING_JOB_START_FAILED'
            }
    
    def get_job_status(self, user_id: int) -> Optional[OnboardingJob]:
        """Get current onboarding job status for user"""
        try:
            job_data = db_optimizer.execute_query(
                "SELECT * FROM onboarding_jobs WHERE user_id = ? ORDER BY started_at DESC LIMIT 1",
                (user_id,)
            )
            
            if not job_data:
                return None
            
            job = job_data[0]
            return OnboardingJob(
                id=job['id'],
                user_id=job['user_id'],
                status=job['status'],
                current_step=job['current_step'],
                progress=job['progress'],
                started_at=datetime.fromisoformat(job['started_at']),
                completed_at=datetime.fromisoformat(job['completed_at']) if job.get('completed_at') else None,
                error_message=job.get('error_message'),
                metadata=json.loads(job.get('metadata', '{}'))
            )
            
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return None
    
    def get_user_job(self, user_id: int) -> Optional[OnboardingJob]:
        """Get user's current job (thread-safe)"""
        with self.job_lock:
            return self.active_jobs.get(user_id)
    
    def _run_onboarding_job(self, job_id: int, user_id: int):
        """Run the complete onboarding job in background"""
        try:
            # Update job status to running
            self._update_job_status(job_id, 'running', 'gmail_sync', 10)
            
            # Step 1: Gmail Sync
            logger.info(f"Starting Gmail sync for user {user_id}")
            sync_result = self._perform_gmail_sync(user_id)
            if not sync_result['success']:
                raise Exception(f"Gmail sync failed: {sync_result['error']}")
            
            self._update_job_status(job_id, 'running', 'lead_extraction', 40)
            
            # Step 2: Lead Extraction
            logger.info(f"Extracting leads for user {user_id}")
            leads_result = self._extract_leads_from_emails(user_id)
            if not leads_result['success']:
                raise Exception(f"Lead extraction failed: {leads_result['error']}")
            
            self._update_job_status(job_id, 'running', 'starter_automations', 70)
            
            # Step 3: Create Starter Automations
            logger.info(f"Creating starter automations for user {user_id}")
            automation_result = self._create_starter_automations(user_id)
            if not automation_result['success']:
                logger.warning(f"Starter automations failed: {automation_result['error']}")
                # Don't fail the job for automation issues
            
            self._update_job_status(job_id, 'running', 'dashboard_seeding', 90)
            
            # Step 4: Dashboard Seeding
            logger.info(f"Seeding dashboard data for user {user_id}")
            seeding_result = self._seed_dashboard_data(user_id)
            if not seeding_result['success']:
                logger.warning(f"Dashboard seeding failed: {seeding_result['error']}")
                # Don't fail the job for seeding issues
            
            # Complete job
            self._update_job_status(job_id, 'completed', 'completed', 100)
            
            logger.info(f"Onboarding job {job_id} completed successfully for user {user_id}")
            
        except Exception as e:
            logger.error(f"Onboarding job {job_id} failed: {e}")
            self._update_job_status(job_id, 'failed', 'error', 0, error_message=str(e))
    
    def _update_job_status(self, job_id: int, status: str, current_step: str, progress: int, error_message: str = None):
        """Update job status in database"""
        try:
            update_fields = ['status = ?', 'current_step = ?', 'progress = ?']
            update_values = [status, current_step, progress]
            
            if status == 'completed':
                update_fields.append('completed_at = ?')
                update_values.append(datetime.now().isoformat())
            
            if error_message:
                update_fields.append('error_message = ?')
                update_values.append(error_message)
            
            update_values.append(job_id)
            
            query = f"UPDATE onboarding_jobs SET {', '.join(update_fields)} WHERE id = ?"
            db_optimizer.execute_query(query, tuple(update_values), fetch=False)
            
            # Update in-memory cache
            job_data = db_optimizer.execute_query(
                "SELECT * FROM onboarding_jobs WHERE id = ?",
                (job_id,)
            )[0]
            
            job = OnboardingJob(
                id=job_data['id'],
                user_id=job_data['user_id'],
                status=job_data['status'],
                current_step=job_data['current_step'],
                progress=job_data['progress'],
                started_at=datetime.fromisoformat(job_data['started_at']),
                completed_at=datetime.fromisoformat(job_data['completed_at']) if job_data.get('completed_at') else None,
                error_message=job_data.get('error_message'),
                metadata=json.loads(job_data.get('metadata', '{}'))
            )
            
            with self.job_lock:
                self.active_jobs[job.user_id] = job
            
        except Exception as e:
            logger.error(f"Error updating job status: {e}")
    
    def _perform_gmail_sync(self, user_id: int) -> Dict[str, Any]:
        """Perform Gmail sync for onboarding"""
        try:
            # Check if Gmail is connected
            if not gmail_oauth_manager.is_gmail_connected(user_id):
                return {
                    'success': False,
                    'error': 'Gmail not connected'
                }
            
            # Start email sync
            sync_result = gmail_sync_manager.start_initial_sync(user_id)
            if not sync_result['success']:
                return sync_result
            
            # Wait for sync to complete (with timeout)
            sync_id = sync_result['sync_id']
            timeout = 300  # 5 minutes
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                sync_status = gmail_sync_manager.get_sync_status(user_id)
                if sync_status:
                    if sync_status.status == 'completed':
                        return {
                            'success': True,
                            'data': {
                                'emails_processed': sync_status.emails_processed,
                                'sync_id': sync_id
                            }
                        }
                    elif sync_status.status == 'failed':
                        return {
                            'success': False,
                            'error': sync_status.error_message or 'Sync failed'
                        }
                
                time.sleep(2)  # Check every 2 seconds
            
            return {
                'success': False,
                'error': 'Sync timeout'
            }
            
        except Exception as e:
            logger.error(f"Error performing Gmail sync: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_leads_from_emails(self, user_id: int) -> Dict[str, Any]:
        """Extract leads from synced emails"""
        try:
            # Get recent email activities
            activities_data = db_optimizer.execute_query(
                """SELECT DISTINCT la.lead_id, l.email, l.name, l.company
                   FROM lead_activities la
                   JOIN leads l ON la.lead_id = l.id
                   WHERE l.user_id = ? AND la.activity_type = 'email_received'
                   AND la.timestamp >= datetime('now', '-7 days')
                   ORDER BY la.timestamp DESC""",
                (user_id,)
            )
            
            leads_created = 0
            for activity in activities_data:
                # Check if this is a new lead or existing
                existing_lead = db_optimizer.execute_query(
                    "SELECT id FROM leads WHERE user_id = ? AND email = ?",
                    (user_id, activity['email'])
                )
                
                if not existing_lead:
                    # Create new lead from email
                    lead_data = {
                        'email': activity['email'],
                        'name': activity['name'] or activity['email'].split('@')[0],
                        'company': activity['company'],
                        'source': 'gmail',
                        'stage': 'new',
                        'notes': 'Auto-created from Gmail sync'
                    }
                    
                    result = enhanced_crm_service.create_lead(user_id, lead_data)
                    if result['success']:
                        leads_created += 1
            
            return {
                'success': True,
                'data': {
                    'leads_created': leads_created,
                    'total_activities': len(activities_data)
                }
            }
            
        except Exception as e:
            logger.error(f"Error extracting leads: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_starter_automations(self, user_id: int) -> Dict[str, Any]:
        """Create starter automations for new users"""
        try:
            automations_created = 0
            
            # Starter Automation 1: Auto-reply to new leads
            auto_reply_rule = {
                'name': 'Welcome New Leads',
                'description': 'Automatically send a welcome message to new leads',
                'trigger_type': 'lead_created',
                'trigger_conditions': {
                    'source': 'gmail'
                },
                'action_type': 'send_email',
                'action_parameters': {
                    'template': 'welcome_new_lead',
                    'delay_minutes': 5,
                    'subject': 'Thank you for reaching out!',
                    'body': 'Hi {{name}},\n\nThank you for contacting us! We\'ve received your message and will get back to you within 24 hours.\n\nBest regards,\n{{business_name}}'
                }
            }
            
            result = automation_engine.create_automation_rule(user_id, auto_reply_rule)
            if result['success']:
                automations_created += 1
            
            # Starter Automation 2: Label invoices
            invoice_label_rule = {
                'name': 'Label Invoices',
                'description': 'Automatically label emails containing invoices',
                'trigger_type': 'keyword_detected',
                'trigger_conditions': {
                    'keywords': ['invoice', 'billing', 'payment', 'receipt'],
                    'subject_contains': True
                },
                'action_type': 'apply_label',
                'action_parameters': {
                    'label': 'Finance',
                    'mark_read': True
                }
            }
            
            result = automation_engine.create_automation_rule(user_id, invoice_label_rule)
            if result['success']:
                automations_created += 1
            
            return {
                'success': True,
                'data': {
                    'automations_created': automations_created
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating starter automations: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _seed_dashboard_data(self, user_id: int) -> Dict[str, Any]:
        """Seed dashboard with initial data"""
        try:
            # Create some sample metrics
            metrics_created = 0
            
            # Get user's leads count
            leads_count = db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM leads WHERE user_id = ?",
                (user_id,)
            )[0]['count']
            
            # Create daily metrics entry
            today = datetime.now().date().isoformat()
            db_optimizer.execute_query(
                """INSERT OR REPLACE INTO metrics_daily 
                   (user_id, day, emails_processed, leads_created, automations_run, automation_errors) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, today, 0, leads_count, 0, 0),
                fetch=False
            )
            metrics_created += 1
            
            return {
                'success': True,
                'data': {
                    'metrics_created': metrics_created,
                    'leads_count': leads_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error seeding dashboard data: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_onboarding_summary(self, user_id: int) -> Dict[str, Any]:
        """Get complete onboarding summary for user"""
        try:
            # Get job status
            job = self.get_job_status(user_id)
            
            # Get user data
            user_data = db_optimizer.execute_query(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            )[0]
            
            # Get Gmail connection status
            gmail_connected = gmail_oauth_manager.is_gmail_connected(user_id)
            
            # Get leads count
            leads_count = db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM leads WHERE user_id = ?",
                (user_id,)
            )[0]['count']
            
            # Get automations count
            automations_count = db_optimizer.execute_query(
                "SELECT COUNT(*) as count FROM automation_rules WHERE user_id = ?",
                (user_id,)
            )[0]['count']
            
            return {
                'success': True,
                'data': {
                    'user': {
                        'id': user_data['id'],
                        'name': user_data['name'],
                        'email': user_data['email'],
                        'onboarding_completed': user_data['onboarding_completed'],
                        'onboarding_step': user_data['onboarding_step']
                    },
                    'job_status': {
                        'status': job.status if job else 'not_started',
                        'current_step': job.current_step if job else None,
                        'progress': job.progress if job else 0,
                        'error_message': job.error_message if job else None
                    },
                    'gmail_connected': gmail_connected,
                    'leads_count': leads_count,
                    'automations_count': automations_count,
                    'ready_for_dashboard': gmail_connected and leads_count > 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting onboarding summary: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Global onboarding orchestrator instance
onboarding_orchestrator = OnboardingOrchestrator()

# Export the onboarding orchestrator
__all__ = ['OnboardingOrchestrator', 'onboarding_orchestrator', 'OnboardingJob']
