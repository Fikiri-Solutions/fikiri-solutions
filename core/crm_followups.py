#!/usr/bin/env python3
"""
Fikiri Solutions - CRM Follow-up Service
Handles automated follow-up generation and sending.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from .crm_service import CRMService, Lead

class CRMFollowupService:
    """Service for managing CRM follow-ups."""
    
    def __init__(self, crm_service: CRMService):
        """Initialize follow-up service."""
        self.crm_service = crm_service
        self.logger = logging.getLogger(__name__)
    
    def generate_followup(self, lead: Lead) -> str:
        """Generate follow-up text for a lead."""
        try:
            # Simple template-based follow-up generation
            templates = {
                'new': f"""Hi {lead.name},

Thank you for your interest in our services. I wanted to follow up on your inquiry and see if you have any questions.

We specialize in helping businesses like {lead.company or 'yours'} streamline their operations and improve efficiency.

Would you be available for a brief call this week to discuss how we can help?

Best regards,
Fikiri Solutions Team""",
                
                'contacted': f"""Hi {lead.name},

I hope you're doing well. I wanted to follow up on our previous conversation about your business needs.

Have you had a chance to review the information I sent? I'd love to hear your thoughts and answer any questions you might have.

Looking forward to hearing from you.

Best regards,
Fikiri Solutions Team""",
                
                'replied': f"""Hi {lead.name},

Thank you for your response! I'm excited about the possibility of working together.

Based on our conversation, I believe we can provide significant value to {lead.company or 'your business'}. 

Would you like to schedule a more detailed discussion about how we can help you achieve your goals?

Best regards,
Fikiri Solutions Team"""
            }
            
            template = templates.get(lead.stage, templates['new'])
            return template
            
        except Exception as e:
            self.logger.error(f"❌ Failed to generate follow-up: {e}")
            return f"Hi {lead.name},\n\nThank you for your interest. Please let me know if you have any questions.\n\nBest regards,\nFikiri Solutions Team"
    
    def batch_followup(self, stage_filter: Optional[str] = None, send: bool = False) -> Dict[str, Any]:
        """Generate follow-ups for multiple leads."""
        try:
            # Get leads to follow up
            leads = self.crm_service.list(stage_filter)
            
            # Filter leads that need follow-up (simple logic)
            followup_leads = []
            for lead in leads:
                if self._needs_followup(lead):
                    followup_leads.append(lead)
            
            results = {
                'count': len(followup_leads),
                'preview': [],
                'sent': 0
            }
            
            for lead in followup_leads:
                followup_text = self.generate_followup(lead)
                
                preview_item = {
                    'lead': f"{lead.name} ({lead.email})",
                    'stage': lead.stage,
                    'text': followup_text[:100] + "..." if len(followup_text) > 100 else followup_text
                }
                results['preview'].append(preview_item)
                
                if send:
                    # In a real implementation, this would send the email
                    self.logger.info(f"📧 Would send follow-up to {lead.email}")
                    results['sent'] += 1
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Failed to batch follow-up: {e}")
            return {'count': 0, 'preview': [], 'sent': 0, 'error': str(e)}
    
    def _needs_followup(self, lead: Lead) -> bool:
        """Determine if a lead needs follow-up."""
        try:
            # Simple logic: follow up if updated more than 3 days ago
            updated_at = datetime.fromisoformat(lead.updated_at)
            days_since_update = (datetime.now() - updated_at).days
            
            # Different follow-up schedules by stage
            followup_schedules = {
                'new': 1,      # Follow up new leads within 1 day
                'contacted': 3, # Follow up contacted leads within 3 days
                'replied': 7,  # Follow up replied leads within 7 days
                'won': 30,     # Follow up won leads within 30 days
                'lost': 90     # Follow up lost leads within 90 days
            }
            
            schedule_days = followup_schedules.get(lead.stage, 7)
            return days_since_update >= schedule_days
            
        except Exception as e:
            self.logger.error(f"❌ Error checking follow-up need: {e}")
            return False
    
    def schedule_followup(self, lead_id: str, days_from_now: int = 7) -> bool:
        """Schedule a follow-up for a specific lead."""
        try:
            lead = self.crm_service.get_lead(lead_id)
            if not lead:
                return False
            
            # Update lead with follow-up schedule
            followup_date = datetime.now() + timedelta(days=days_from_now)
            updates = {
                'notes': f"{lead.notes}\nFollow-up scheduled for: {followup_date.strftime('%Y-%m-%d')}".strip(),
                'stage': 'followup_scheduled'
            }
            
            return self.crm_service.update_lead(lead_id, updates) is not None
            
        except Exception as e:
            self.logger.error(f"❌ Failed to schedule follow-up: {e}")
            return False
