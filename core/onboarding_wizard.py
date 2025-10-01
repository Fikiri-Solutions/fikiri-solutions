#!/usr/bin/env python3
"""
Enhanced Onboarding Wizard System
3-step onboarding process: Company Setup → Gmail Connect → Data Preview
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from core.database_optimization import db_optimizer
from core.tenant_manager import tenant_manager
from core.google_oauth import google_oauth_manager
from core.email_jobs import email_job_manager

logger = logging.getLogger(__name__)

class OnboardingStep(Enum):
    """Onboarding step enumeration"""
    COMPANY_SETUP = 1
    GMAIL_CONNECT = 2
    DATA_PREVIEW = 3
    COMPLETED = 4

@dataclass
class OnboardingProgress:
    """Onboarding progress data structure"""
    user_id: int
    current_step: int
    completed_steps: List[int]
    company_data: Dict[str, Any]
    gmail_connected: bool
    sync_status: Dict[str, Any]
    preview_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class OnboardingWizard:
    """Enhanced onboarding wizard with 3-step process"""
    
    def __init__(self):
        self._initialize_tables()
    
    def _initialize_tables(self):
        """Initialize database tables for onboarding tracking"""
        try:
            # Create onboarding progress table
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS onboarding_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    current_step INTEGER DEFAULT 1,
                    completed_steps TEXT DEFAULT '[]',
                    company_data TEXT DEFAULT '{}',
                    gmail_connected BOOLEAN DEFAULT FALSE,
                    sync_status TEXT DEFAULT '{}',
                    preview_data TEXT DEFAULT '{}',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_completed BOOLEAN DEFAULT FALSE,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """, fetch=False)
            
            # Create index
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_onboarding_progress_user_id 
                ON onboarding_progress (user_id)
            """, fetch=False)
            
            # Create onboarding jobs table for background tasks
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS onboarding_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    job_type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    progress INTEGER DEFAULT 0,
                    result TEXT DEFAULT '{}',
                    error_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    started_at DATETIME,
                    completed_at DATETIME,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """, fetch=False)
            
            logger.info("✅ Onboarding wizard tables initialized")
            
        except Exception as e:
            logger.error(f"❌ Onboarding wizard table initialization failed: {e}")
    
    def start_onboarding(self, user_id: int, company_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start the onboarding process for a user"""
        try:
            # Check if onboarding already exists
            existing = db_optimizer.execute_query("""
                SELECT * FROM onboarding_progress WHERE user_id = ?
            """, (user_id,))
            
            if existing:
                # Update existing onboarding
                progress = existing[0]
                current_step = progress['current_step']
                completed_steps = json.loads(progress['completed_steps'])
                
                return {
                    'success': True,
                    'onboarding_id': progress['id'],
                    'current_step': current_step,
                    'completed_steps': completed_steps,
                    'company_data': json.loads(progress['company_data']),
                    'gmail_connected': progress['gmail_connected'],
                    'sync_status': json.loads(progress['sync_status']),
                    'preview_data': json.loads(progress['preview_data'])
                }
            
            # Create new onboarding progress
            onboarding_id = db_optimizer.execute_query("""
                INSERT INTO onboarding_progress 
                (user_id, current_step, company_data, completed_steps)
                VALUES (?, 1, ?, '[]')
            """, (
                user_id,
                json.dumps(company_data or {})
            ), fetch=False)
            
            # Update user onboarding status
            db_optimizer.execute_query("""
                UPDATE users SET 
                    metadata = json_set(metadata, '$.onboarding_step', 1),
                    metadata = json_set(metadata, '$.onboarding_completed', FALSE)
                WHERE id = ?
            """, (user_id,), fetch=False)
            
            logger.info(f"✅ Started onboarding for user {user_id}")
            
            return {
                'success': True,
                'onboarding_id': onboarding_id,
                'current_step': 1,
                'completed_steps': [],
                'company_data': company_data or {},
                'gmail_connected': False,
                'sync_status': {},
                'preview_data': {}
            }
            
        except Exception as e:
            logger.error(f"❌ Onboarding start failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'ONBOARDING_START_FAILED'
            }
    
    def complete_step(self, user_id: int, step: int, step_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Complete a specific onboarding step"""
        try:
            # Get current progress
            progress_data = db_optimizer.execute_query("""
                SELECT * FROM onboarding_progress WHERE user_id = ?
            """, (user_id,))
            
            if not progress_data:
                return {
                    'success': False,
                    'error': 'Onboarding not found',
                    'error_code': 'ONBOARDING_NOT_FOUND'
                }
            
            progress = progress_data[0]
            current_step = progress['current_step']
            completed_steps = json.loads(progress['completed_steps'])
            
            # Validate step progression
            if step != current_step:
                return {
                    'success': False,
                    'error': f'Invalid step progression. Expected step {current_step}, got {step}',
                    'error_code': 'INVALID_STEP_PROGRESSION'
                }
            
            # Process step-specific data
            if step == OnboardingStep.COMPANY_SETUP.value:
                result = self._complete_company_setup(user_id, step_data or {})
            elif step == OnboardingStep.GMAIL_CONNECT.value:
                result = self._complete_gmail_connect(user_id, step_data or {})
            elif step == OnboardingStep.DATA_PREVIEW.value:
                result = self._complete_data_preview(user_id, step_data or {})
            else:
                return {
                    'success': False,
                    'error': f'Invalid step: {step}',
                    'error_code': 'INVALID_STEP'
                }
            
            if not result['success']:
                return result
            
            # Update progress
            completed_steps.append(step)
            next_step = step + 1 if step < OnboardingStep.COMPLETED.value else OnboardingStep.COMPLETED.value
            
            # Update database
            update_fields = []
            update_values = []
            
            if step == OnboardingStep.COMPANY_SETUP.value:
                update_fields.append("company_data = ?")
                update_values.append(json.dumps(step_data or {}))
            elif step == OnboardingStep.GMAIL_CONNECT.value:
                update_fields.append("gmail_connected = TRUE")
                update_fields.append("sync_status = ?")
                update_values.append(json.dumps(step_data or {}))
            elif step == OnboardingStep.DATA_PREVIEW.value:
                update_fields.append("preview_data = ?")
                update_values.append(json.dumps(step_data or {}))
            
            update_fields.extend([
                "current_step = ?",
                "completed_steps = ?",
                "updated_at = datetime('now')"
            ])
            update_values.extend([next_step, json.dumps(completed_steps), user_id])
            
            query = f"""
                UPDATE onboarding_progress 
                SET {', '.join(update_fields)}
                WHERE user_id = ?
            """
            
            db_optimizer.execute_query(query, tuple(update_values), fetch=False)
            
            # Update user metadata
            db_optimizer.execute_query("""
                UPDATE users SET 
                    metadata = json_set(metadata, '$.onboarding_step', ?),
                    metadata = json_set(metadata, '$.onboarding_completed', ?)
                WHERE id = ?
            """, (
                next_step,
                next_step == OnboardingStep.COMPLETED.value,
                user_id
            ), fetch=False)
            
            # Send onboarding email for completed step
            try:
                user_data = db_optimizer.execute_query("""
                    SELECT email, name FROM users WHERE id = ?
                """, (user_id,))
                
                if user_data:
                    user = user_data[0]
                    email_job_manager.queue_onboarding_email(
                        user_id,
                        user['email'],
                        user['name'],
                        step,
                        step_data.get('company_name') if step_data else None
                    )
            except Exception as e:
                logger.warning(f"Failed to queue onboarding email: {e}")
            
            # Check if onboarding is complete
            is_completed = next_step == OnboardingStep.COMPLETED.value
            if is_completed:
                db_optimizer.execute_query("""
                    UPDATE onboarding_progress 
                    SET is_completed = TRUE, completed_at = datetime('now')
                    WHERE user_id = ?
                """, (user_id,), fetch=False)
            
            logger.info(f"✅ Completed onboarding step {step} for user {user_id}")
            
            return {
                'success': True,
                'current_step': next_step,
                'completed_steps': completed_steps,
                'is_completed': is_completed,
                'next_action': self._get_next_action(next_step)
            }
            
        except Exception as e:
            logger.error(f"❌ Step completion failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'STEP_COMPLETION_FAILED'
            }
    
    def _complete_company_setup(self, user_id: int, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete company setup step"""
        try:
            # Validate required fields
            required_fields = ['business_name', 'industry', 'team_size']
            for field in required_fields:
                if field not in step_data or not step_data[field]:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}',
                        'error_code': 'MISSING_FIELD'
                    }
            
            # Update company information
            company_result = tenant_manager.update_company(
                user_id,  # Assuming user_id maps to company_id for now
                {
                    'name': step_data['business_name'],
                    'industry': step_data['industry'],
                    'team_size': step_data['team_size']
                }
            )
            
            if not company_result:
                return {
                    'success': False,
                    'error': 'Failed to update company information',
                    'error_code': 'COMPANY_UPDATE_FAILED'
                }
            
            return {
                'success': True,
                'data': step_data
            }
            
        except Exception as e:
            logger.error(f"❌ Company setup completion failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'COMPANY_SETUP_FAILED'
            }
    
    def _complete_gmail_connect(self, user_id: int, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete Gmail connection step"""
        try:
            # Check if Gmail is already connected
            token_data = db_optimizer.execute_query("""
                SELECT * FROM google_oauth_tokens 
                WHERE user_id = ? AND is_active = TRUE
            """, (user_id,))
            
            if not token_data:
                return {
                    'success': False,
                    'error': 'Gmail not connected. Please complete OAuth flow first.',
                    'error_code': 'GMAIL_NOT_CONNECTED'
                }
            
            # Start background sync job
            sync_job_id = self._start_gmail_sync_job(user_id)
            
            return {
                'success': True,
                'data': {
                    'gmail_connected': True,
                    'sync_job_id': sync_job_id,
                    'sync_status': 'started'
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Gmail connect completion failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'GMAIL_CONNECT_FAILED'
            }
    
    def _complete_data_preview(self, user_id: int, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete data preview step"""
        try:
            # Get sync status
            sync_jobs = db_optimizer.execute_query("""
                SELECT * FROM onboarding_jobs 
                WHERE user_id = ? AND job_type = 'gmail_sync'
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,))
            
            sync_status = 'completed'
            if sync_jobs:
                job = sync_jobs[0]
                sync_status = job['status']
            
            # Generate preview data
            preview_data = self._generate_preview_data(user_id)
            
            return {
                'success': True,
                'data': {
                    'sync_status': sync_status,
                    'preview_data': preview_data
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Data preview completion failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'DATA_PREVIEW_FAILED'
            }
    
    def _start_gmail_sync_job(self, user_id: int) -> str:
        """Start background Gmail sync job"""
        try:
            from core.gmail_sync_jobs import gmail_sync_job_manager
            
            # Queue actual sync job
            job_id = gmail_sync_job_manager.queue_sync_job(
                user_id, 
                sync_type='onboarding',
                metadata={
                    'source': 'onboarding',
                    'created_at': datetime.utcnow().isoformat()
                }
            )
            
            if job_id:
                # Create onboarding job record for tracking
                db_optimizer.execute_query("""
                    INSERT INTO onboarding_jobs 
                    (user_id, job_type, status, metadata)
                    VALUES (?, 'gmail_sync', 'pending', ?)
                """, (
                    user_id,
                    json.dumps({
                        'job_id': job_id,
                        'created_at': datetime.utcnow().isoformat()
                    })
                ), fetch=False)
            
            return job_id
            
        except Exception as e:
            logger.error(f"❌ Gmail sync job start failed: {e}")
            return None
    
    def _generate_preview_data(self, user_id: int) -> Dict[str, Any]:
        """Generate preview data for the user"""
        try:
            from core.gmail_sync_jobs import gmail_sync_job_manager
            
            # Get actual sync results
            sync_stats = gmail_sync_job_manager.get_user_sync_stats(user_id)
            
            # Get top contacts with lead scores
            top_contacts = db_optimizer.execute_query("""
                SELECT email, name, company, lead_score, contact_count
                FROM contacts 
                WHERE user_id = ? AND lead_score > 0
                ORDER BY lead_score DESC, contact_count DESC
                LIMIT 5
            """, (user_id,))
            
            # Get recent emails
            recent_emails = db_optimizer.execute_query("""
                SELECT subject, sender, date, lead_score
                FROM synced_emails 
                WHERE user_id = ? 
                ORDER BY date DESC
                LIMIT 5
            """, (user_id,))
            
            # Generate AI insights
            ai_insights = []
            for contact in top_contacts:
                if contact['lead_score'] > 50:
                    ai_insights.append({
                        'type': 'lead_score',
                        'contact': contact['email'],
                        'name': contact['name'],
                        'company': contact['company'],
                        'score': contact['lead_score'],
                        'reason': self._get_lead_reason(contact['lead_score'], contact['contact_count'])
                    })
            
            # Generate automation suggestions based on data
            automation_suggestions = self._generate_automation_suggestions(sync_stats, top_contacts)
            
            preview_data = {
                'emails_synced': sync_stats.get('total_emails', 0),
                'contacts_found': sync_stats.get('total_contacts', 0),
                'leads_identified': sync_stats.get('total_leads', 0),
                'recent_emails': sync_stats.get('recent_emails', 0),
                'ai_insights': ai_insights,
                'top_contacts': [
                    {
                        'email': contact['email'],
                        'name': contact['name'],
                        'company': contact['company'],
                        'lead_score': contact['lead_score'],
                        'contact_count': contact['contact_count']
                    }
                    for contact in top_contacts
                ],
                'recent_emails_preview': [
                    {
                        'subject': email['subject'],
                        'sender': email['sender'],
                        'date': email['date'],
                        'lead_score': email['lead_score']
                    }
                    for email in recent_emails
                ],
                'automation_suggestions': automation_suggestions,
                'next_steps': self._get_next_steps(sync_stats, ai_insights)
            }
            
            return preview_data
            
        except Exception as e:
            logger.error(f"❌ Preview data generation failed: {e}")
            return {
                'emails_synced': 0,
                'contacts_found': 0,
                'leads_identified': 0,
                'ai_insights': [],
                'automation_suggestions': [],
                'next_steps': []
            }
    
    def _get_lead_reason(self, score: int, contact_count: int) -> str:
        """Get reason for lead score"""
        if score >= 80:
            return "High-value prospect with strong engagement"
        elif score >= 60:
            return "Good prospect with regular communication"
        elif score >= 40:
            return "Potential lead with some engagement"
        else:
            return "Low engagement, needs nurturing"
    
    def _generate_automation_suggestions(self, sync_stats: Dict[str, Any], top_contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate automation suggestions based on data"""
        suggestions = []
        
        # Email sequence suggestions
        if sync_stats.get('total_contacts', 0) > 0:
            suggestions.append({
                'type': 'email_sequence',
                'name': 'Welcome Series',
                'description': 'Automated welcome emails for new contacts',
                'priority': 'high',
                'estimated_impact': 'Increase engagement by 25%'
            })
        
        # Lead nurturing suggestions
        if sync_stats.get('total_leads', 0) > 0:
            suggestions.append({
                'type': 'lead_nurturing',
                'name': 'Lead Nurturing Campaign',
                'description': 'Personalized follow-up sequences for high-value leads',
                'priority': 'high',
                'estimated_impact': 'Convert 15% more leads'
            })
        
        # Meeting follow-up suggestions
        if any('meeting' in contact.get('name', '').lower() or 'meeting' in contact.get('company', '').lower() for contact in top_contacts):
            suggestions.append({
                'type': 'follow_up',
                'name': 'Meeting Follow-up',
                'description': 'Automated follow-up after meetings',
                'priority': 'medium',
                'estimated_impact': 'Improve meeting outcomes by 30%'
            })
        
        # CRM integration suggestions
        if sync_stats.get('total_contacts', 0) > 10:
            suggestions.append({
                'type': 'crm_integration',
                'name': 'CRM Sync',
                'description': 'Sync contacts with your CRM system',
                'priority': 'medium',
                'estimated_impact': 'Streamline contact management'
            })
        
        return suggestions
    
    def _get_next_steps(self, sync_stats: Dict[str, Any], ai_insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get next steps based on data analysis"""
        next_steps = []
        
        # If no data synced yet
        if sync_stats.get('total_emails', 0) == 0:
            next_steps.append({
                'action': 'sync_emails',
                'title': 'Sync Your Emails',
                'description': 'Connect your Gmail to start syncing emails and contacts',
                'priority': 'high',
                'url': '/onboarding/2'
            })
        
        # If data synced but no leads identified
        elif sync_stats.get('total_leads', 0) == 0:
            next_steps.append({
                'action': 'identify_leads',
                'title': 'Identify High-Value Leads',
                'description': 'Use AI to identify and score your most valuable contacts',
                'priority': 'high',
                'url': '/dashboard/leads'
            })
        
        # If leads identified but no automations
        elif sync_stats.get('total_leads', 0) > 0:
            next_steps.append({
                'action': 'create_automations',
                'title': 'Set Up Automations',
                'description': 'Create automated workflows for your high-value leads',
                'priority': 'medium',
                'url': '/dashboard/automations'
            })
        
        # General next steps
        next_steps.extend([
            {
                'action': 'explore_dashboard',
                'title': 'Explore Your Dashboard',
                'description': 'Get familiar with your new Fikiri workspace',
                'priority': 'low',
                'url': '/dashboard'
            },
            {
                'action': 'connect_integrations',
                'title': 'Connect Integrations',
                'description': 'Connect additional tools like CRM, calendar, and more',
                'priority': 'low',
                'url': '/dashboard/integrations'
            }
        ])
        
        return next_steps
    
    def _get_next_action(self, step: int) -> Dict[str, Any]:
        """Get next action for the current step"""
        if step == OnboardingStep.COMPANY_SETUP.value:
            return {
                'action': 'connect_gmail',
                'url': '/onboarding/2',
                'description': 'Connect your Gmail to start syncing emails'
            }
        elif step == OnboardingStep.GMAIL_CONNECT.value:
            return {
                'action': 'preview_data',
                'url': '/onboarding/3',
                'description': 'Preview your synced data and AI insights'
            }
        elif step == OnboardingStep.DATA_PREVIEW.value:
            return {
                'action': 'complete_onboarding',
                'url': '/dashboard',
                'description': 'Complete onboarding and access your dashboard'
            }
        else:
            return {
                'action': 'dashboard',
                'url': '/dashboard',
                'description': 'Access your dashboard'
            }
    
    def get_onboarding_status(self, user_id: int) -> Dict[str, Any]:
        """Get current onboarding status for a user"""
        try:
            progress_data = db_optimizer.execute_query("""
                SELECT * FROM onboarding_progress WHERE user_id = ?
            """, (user_id,))
            
            if not progress_data:
                return {
                    'success': False,
                    'error': 'Onboarding not found',
                    'error_code': 'ONBOARDING_NOT_FOUND'
                }
            
            progress = progress_data[0]
            
            return {
                'success': True,
                'current_step': progress['current_step'],
                'completed_steps': json.loads(progress['completed_steps']),
                'company_data': json.loads(progress['company_data']),
                'gmail_connected': progress['gmail_connected'],
                'sync_status': json.loads(progress['sync_status']),
                'preview_data': json.loads(progress['preview_data']),
                'is_completed': progress['is_completed'],
                'created_at': progress['created_at'],
                'updated_at': progress['updated_at']
            }
            
        except Exception as e:
            logger.error(f"❌ Onboarding status retrieval failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'STATUS_RETRIEVAL_FAILED'
            }
    
    def get_sync_job_status(self, user_id: int) -> Dict[str, Any]:
        """Get Gmail sync job status"""
        try:
            sync_jobs = db_optimizer.execute_query("""
                SELECT * FROM onboarding_jobs 
                WHERE user_id = ? AND job_type = 'gmail_sync'
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,))
            
            if not sync_jobs:
                return {
                    'success': False,
                    'error': 'No sync job found',
                    'error_code': 'NO_SYNC_JOB'
                }
            
            job = sync_jobs[0]
            
            return {
                'success': True,
                'job_id': job['id'],
                'status': job['status'],
                'progress': job['progress'],
                'result': json.loads(job['result']) if job['result'] else {},
                'error_message': job['error_message'],
                'created_at': job['created_at'],
                'started_at': job['started_at'],
                'completed_at': job['completed_at']
            }
            
        except Exception as e:
            logger.error(f"❌ Sync job status retrieval failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'SYNC_STATUS_FAILED'
            }

# Global onboarding wizard
onboarding_wizard = OnboardingWizard()
