"""
Automated Follow-up System for Fikiri Solutions
Handles automated follow-ups using OpenAI + Gmail integration
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

# Optional dependencies
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    from core.minimal_config import get_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    get_config = None

try:
    from core.gmail_oauth import gmail_oauth_manager
    GMAIL_OAUTH_AVAILABLE = True
except ImportError:
    GMAIL_OAUTH_AVAILABLE = False
    gmail_oauth_manager = None

try:
    from core.database_optimization import db_optimizer
    DB_OPTIMIZER_AVAILABLE = True
except ImportError:
    DB_OPTIMIZER_AVAILABLE = False
    db_optimizer = None

try:
    from core.email_action_handlers import get_email_action_handler
    EMAIL_ACTION_HANDLERS_AVAILABLE = True
except ImportError:
    EMAIL_ACTION_HANDLERS_AVAILABLE = False
    get_email_action_handler = None

logger = logging.getLogger(__name__)

@dataclass
class FollowUpTemplate:
    """Follow-up template data structure"""
    id: str
    name: str
    stage: str
    delay_days: int
    subject_template: str
    body_template: str
    is_active: bool

@dataclass
class FollowUpTask:
    """Follow-up task data structure"""
    id: str
    lead_id: str
    user_id: int
    template_id: str
    scheduled_for: datetime
    status: str  # pending, sent, failed, cancelled
    created_at: datetime

class AutomatedFollowUpSystem:
    """Automated follow-up system with OpenAI + Gmail integration"""
    
    def __init__(self):
        self.openai_client = None
        self._init_openai()
        self.email_handler = get_email_action_handler()
        
        # Default follow-up templates
        self.default_templates = [
            FollowUpTemplate(
                id="initial_contact",
                name="Initial Contact Follow-up",
                stage="new",
                delay_days=1,
                subject_template="Following up on your inquiry - {company_name}",
                body_template="""Hi {name},

Thank you for your interest in our services. I wanted to follow up on your recent inquiry about {service_type}.

I'd love to schedule a brief call to discuss your specific needs and how we can help your business grow. Are you available for a 15-minute conversation this week?

Best regards,
{user_name}""",
                is_active=True
            ),
            FollowUpTemplate(
                id="proposal_followup",
                name="Proposal Follow-up",
                stage="proposal",
                delay_days=3,
                subject_template="Quick check-in on your proposal - {company_name}",
                body_template="""Hi {name},

I hope you're doing well. I wanted to follow up on the proposal I sent for {service_type}.

Do you have any questions about the proposal? I'm here to help clarify anything or discuss next steps.

Looking forward to hearing from you.

Best regards,
{user_name}""",
                is_active=True
            ),
            FollowUpTemplate(
                id="final_followup",
                name="Final Follow-up",
                stage="qualified",
                delay_days=7,
                subject_template="Last check-in - {company_name}",
                body_template="""Hi {name},

I wanted to reach out one more time regarding your interest in our {service_type} services.

If you're not ready to move forward right now, I completely understand. I'll keep your information on file and reach out again in a few months.

If you have any questions in the meantime, please don't hesitate to reach out.

Best regards,
{user_name}""",
                is_active=True
            )
        ]
    
    def _init_openai(self):
        """Initialize OpenAI client"""
        try:
            config = get_config()
            api_key = getattr(config, 'openai_api_key', '')
            if api_key:
                openai.api_key = api_key
                self.openai_client = openai
                logger.info("✅ OpenAI client initialized")
            else:
                logger.warning("⚠️ OpenAI API key not configured")
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI: {e}")
    
    def create_follow_up_task(self, lead_id: str, user_id: int, stage: str) -> Dict[str, Any]:
        """Create a follow-up task for a lead"""
        try:
            # Get appropriate template for stage
            template = self._get_template_for_stage(stage)
            if not template:
                return {"success": False, "error": f"No template found for stage: {stage}"}
            
            # Calculate scheduled time
            scheduled_for = datetime.now() + timedelta(days=template.delay_days)
            
            # Generate task ID
            task_id = f"followup_{lead_id}_{int(scheduled_for.timestamp())}"
            
            # Store follow-up task
            query = """
                INSERT INTO follow_up_tasks (
                    id, lead_id, user_id, template_id, scheduled_for, 
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            values = (
                task_id,
                lead_id,
                user_id,
                template.id,
                scheduled_for.isoformat(),
                'pending',
                datetime.now().isoformat()
            )
            
            db_optimizer.execute_query(query, values, fetch=False)
            
            logger.info(f"✅ Follow-up task created: {task_id}")
            return {"success": True, "task_id": task_id}
            
        except Exception as e:
            logger.error(f"❌ Failed to create follow-up task: {e}")
            return {"success": False, "error": str(e)}
    
    def process_pending_follow_ups(self) -> Dict[str, Any]:
        """Process all pending follow-up tasks"""
        try:
            # Get pending tasks
            query = """
                SELECT ft.*, l.email, l.name, l.company, l.stage, l.meta
                FROM follow_up_tasks ft
                JOIN leads l ON ft.lead_id = l.id
                WHERE ft.status = 'pending' 
                AND ft.scheduled_for <= ?
            """
            
            now = datetime.now().isoformat()
            tasks = db_optimizer.execute_query(query, (now,))
            
            processed_count = 0
            failed_count = 0
            
            for task_data in tasks:
                try:
                    result = self._send_follow_up(task_data)
                    if result['success']:
                        processed_count += 1
                        self._update_task_status(task_data['id'], 'sent')
                    else:
                        failed_count += 1
                        self._update_task_status(task_data['id'], 'failed')
                        logger.error(f"❌ Follow-up failed: {result.get('error')}")
                        
                except Exception as e:
                    failed_count += 1
                    self._update_task_status(task_data['id'], 'failed')
                    logger.error(f"❌ Follow-up processing error: {e}")
            
            logger.info(f"✅ Processed {processed_count} follow-ups, {failed_count} failed")
            return {
                "success": True,
                "processed": processed_count,
                "failed": failed_count
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process follow-ups: {e}")
            return {"success": False, "error": str(e)}
    
    def _send_follow_up(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a follow-up email"""
        try:
            # Get template
            template = self._get_template_by_id(task_data['template_id'])
            if not template:
                return {"success": False, "error": "Template not found"}
            
            # Prepare email content
            email_content = self._prepare_email_content(template, task_data)
            
            # Get user's Gmail tokens
            token = gmail_oauth_manager.get_user_tokens(task_data['user_id'])
            if not token:
                return {"success": False, "error": "No Gmail tokens found"}
            
            # Send email using email action handler
            result = self.email_handler.send_ai_response(
                task_data['user_id'],
                f"followup_{task_data['id']}",  # Use task ID as email ID
                email_content['body']
            )
            
            if result['success']:
                # Log the follow-up activity
                self._log_follow_up_activity(task_data, email_content)
                return {"success": True}
            else:
                return {"success": False, "error": result.get('error')}
                
        except Exception as e:
            logger.error(f"❌ Failed to send follow-up: {e}")
            return {"success": False, "error": str(e)}
    
    def _prepare_email_content(self, template: FollowUpTemplate, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare email content using OpenAI for personalization"""
        try:
            # Extract lead data
            lead_meta = json.loads(task_data.get('meta', '{}'))
            
            # Prepare context for OpenAI
            context = {
                "lead_name": task_data.get('name', ''),
                "company_name": task_data.get('company', ''),
                "lead_stage": task_data.get('stage', ''),
                "service_type": lead_meta.get('service_type', 'our services'),
                "user_name": "The Fikiri Team"  # Could be fetched from user profile
            }
            
            # Use OpenAI to personalize the content
            if self.openai_client:
                try:
                    prompt = f"""
                    Personalize this follow-up email template for a lead:
                    
                    Template Subject: {template.subject_template}
                    Template Body: {template.body_template}
                    
                    Lead Context:
                    - Name: {context['lead_name']}
                    - Company: {context['company_name']}
                    - Stage: {context['lead_stage']}
                    - Service Interest: {context['service_type']}
                    
                    Make it personal, professional, and engaging. Keep the same structure but improve the language.
                    Return JSON with 'subject' and 'body' fields.
                    """
                    
                    response = self.openai_client.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=500,
                        temperature=0.7
                    )
                    
                    ai_content = json.loads(response.choices[0].message.content)
                    return {
                        "subject": ai_content.get('subject', template.subject_template),
                        "body": ai_content.get('body', template.body_template)
                    }
                    
                except Exception as e:
                    logger.warning(f"⚠️ OpenAI personalization failed: {e}")
            
            # Fallback to template with simple substitution
            subject = template.subject_template.format(**context)
            body = template.body_template.format(**context)
            
            return {"subject": subject, "body": body}
            
        except Exception as e:
            logger.error(f"❌ Failed to prepare email content: {e}")
            return {
                "subject": template.subject_template,
                "body": template.body_template
            }
    
    def _get_template_for_stage(self, stage: str) -> Optional[FollowUpTemplate]:
        """Get template for a specific stage"""
        for template in self.default_templates:
            if template.stage == stage and template.is_active:
                return template
        return None
    
    def _get_template_by_id(self, template_id: str) -> Optional[FollowUpTemplate]:
        """Get template by ID"""
        for template in self.default_templates:
            if template.id == template_id:
                return template
        return None
    
    def _update_task_status(self, task_id: str, status: str):
        """Update follow-up task status"""
        try:
            query = "UPDATE follow_up_tasks SET status = ? WHERE id = ?"
            db_optimizer.execute_query(query, (status, task_id), fetch=False)
        except Exception as e:
            logger.error(f"❌ Failed to update task status: {e}")
    
    def _log_follow_up_activity(self, task_data: Dict[str, Any], email_content: Dict[str, Any]):
        """Log follow-up activity"""
        try:
            query = """
                INSERT INTO lead_activities (
                    lead_id, activity_type, description, timestamp, metadata
                ) VALUES (?, ?, ?, ?, ?)
            """
            
            values = (
                task_data['lead_id'],
                'follow_up_sent',
                f"Automated follow-up sent: {email_content['subject']}",
                datetime.now().isoformat(),
                json.dumps({
                    'template_id': task_data['template_id'],
                    'email_subject': email_content['subject'],
                    'task_id': task_data['id']
                })
            )
            
            db_optimizer.execute_query(query, values, fetch=False)
            
        except Exception as e:
            logger.error(f"❌ Failed to log follow-up activity: {e}")
    
    def get_follow_up_stats(self, user_id: int) -> Dict[str, Any]:
        """Get follow-up statistics"""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as sent,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM follow_up_tasks 
                WHERE user_id = ?
            """
            
            stats = db_optimizer.execute_query(query, (user_id,))
            if stats:
                return {"success": True, "data": stats[0]}
            else:
                return {"success": True, "data": {"total_tasks": 0, "pending": 0, "sent": 0, "failed": 0}}
                
        except Exception as e:
            logger.error(f"❌ Failed to get follow-up stats: {e}")
            return {"success": False, "error": str(e)}

# Global instance
follow_up_system = None

def get_follow_up_system() -> Optional[AutomatedFollowUpSystem]:
    """Get the global follow-up system instance"""
    global follow_up_system
    
    if follow_up_system is None:
        follow_up_system = AutomatedFollowUpSystem()
    
    return follow_up_system
