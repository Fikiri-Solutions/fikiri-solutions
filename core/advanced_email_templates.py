"""
Advanced Email Templates System for Fikiri Solutions
Industry-specific templates with dynamic content generation
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from core.minimal_config import get_config

logger = logging.getLogger(__name__)

@dataclass
class EmailTemplate:
    """Email template data structure"""
    id: str
    name: str
    industry: str
    intent: str
    subject_template: str
    body_template: str
    variables: List[str]
    is_active: bool
    created_at: datetime

class AdvancedEmailTemplates:
    """Advanced email templates with industry-specific content"""
    
    def __init__(self):
        self.templates = self._load_default_templates()
        self.industry_contexts = self._load_industry_contexts()
    
    def _load_default_templates(self) -> Dict[str, EmailTemplate]:
        """Load default email templates"""
        templates = {}
        
        # Landscaping Industry Templates
        landscaping_templates = [
            EmailTemplate(
                id="landscaping_quote_request",
                name="Landscaping Quote Request Response",
                industry="landscaping",
                intent="lead_inquiry",
                subject_template="Thank you for your landscaping inquiry - {company_name}",
                body_template="""Hi {sender_name},

Thank you for reaching out to {company_name} regarding your landscaping needs!

I'm excited to learn more about your project. Based on your inquiry about {service_type}, I'd love to schedule a free consultation to:

• Assess your property and discuss your vision
• Provide a detailed quote tailored to your needs
• Answer any questions about our services
• Explain our process and timeline

Our team specializes in:
- {service_specialties}
- {service_areas}

I'm available for a consultation this week. Would you prefer a phone call or an in-person visit?

Best regards,
{user_name}
{company_name}
{contact_info}""",
                variables=["sender_name", "company_name", "service_type", "service_specialties", "service_areas", "user_name", "contact_info"],
                is_active=True,
                created_at=datetime.now()
            ),
            EmailTemplate(
                id="landscaping_follow_up",
                name="Landscaping Follow-up",
                industry="landscaping",
                intent="follow_up",
                subject_template="Following up on your landscaping project - {company_name}",
                body_template="""Hi {sender_name},

I wanted to follow up on our recent discussion about your landscaping project.

I hope you've had a chance to review the proposal I sent. I'm here to answer any questions you might have about:

• The project timeline and phases
• Materials and plant selections
• Maintenance requirements
• Payment options

If you're ready to move forward, I can schedule the project start date. If you need more time to decide, I completely understand.

Please let me know how I can help!

Best regards,
{user_name}
{company_name}""",
                variables=["sender_name", "company_name", "user_name"],
                is_active=True,
                created_at=datetime.now()
            ),
            EmailTemplate(
                id="landscaping_service_reminder",
                name="Landscaping Service Reminder",
                industry="landscaping",
                intent="service_reminder",
                subject_template="Upcoming service reminder - {company_name}",
                body_template="""Hi {sender_name},

This is a friendly reminder that we have your {service_type} scheduled for {service_date}.

Our team will arrive between {time_window} and will complete:
• {service_tasks}

Please ensure:
• Access to the service area is clear
• Any special instructions are noted
• Contact information is up to date

If you need to reschedule or have any questions, please let me know as soon as possible.

Thank you for choosing {company_name}!

Best regards,
{user_name}
{company_name}""",
                variables=["sender_name", "company_name", "service_type", "service_date", "time_window", "service_tasks", "user_name"],
                is_active=True,
                created_at=datetime.now()
            )
        ]
        
        # Real Estate Industry Templates
        real_estate_templates = [
            EmailTemplate(
                id="real_estate_listing_inquiry",
                name="Real Estate Listing Inquiry Response",
                industry="real_estate",
                intent="lead_inquiry",
                subject_template="Thank you for your interest in {property_address}",
                body_template="""Hi {sender_name},

Thank you for your interest in {property_address}!

I'm excited to help you with this property. Here's what I can provide:

• Detailed property information and photos
• Neighborhood insights and market analysis
• Financing options and pre-approval assistance
• Schedule a private showing at your convenience

The property features:
- {property_features}
- {property_amenities}

I'm available to answer any questions and schedule a viewing. Would you prefer a virtual tour or an in-person visit?

Best regards,
{user_name}
{company_name}
{contact_info}""",
                variables=["sender_name", "company_name", "property_address", "property_features", "property_amenities", "user_name", "contact_info"],
                is_active=True,
                created_at=datetime.now()
            )
        ]
        
        # Healthcare Industry Templates
        healthcare_templates = [
            EmailTemplate(
                id="healthcare_appointment_request",
                name="Healthcare Appointment Request Response",
                industry="healthcare",
                intent="appointment_request",
                subject_template="Appointment confirmation - {clinic_name}",
                body_template="""Dear {sender_name},

Thank you for requesting an appointment with {clinic_name}.

We have received your request for:
• Service: {service_type}
• Preferred date: {preferred_date}
• Reason: {appointment_reason}

Our team will contact you within 24 hours to confirm your appointment time.

Before your visit, please:
• Complete the patient intake form
• Bring your insurance card and ID
• Arrive 15 minutes early for check-in

If you have any questions or need to reschedule, please call us at {phone_number}.

We look forward to serving you!

Best regards,
{user_name}
{clinic_name}""",
                variables=["sender_name", "clinic_name", "service_type", "preferred_date", "appointment_reason", "phone_number", "user_name"],
                is_active=True,
                created_at=datetime.now()
            )
        ]
        
        # Add all templates to the dictionary
        for template in landscaping_templates + real_estate_templates + healthcare_templates:
            templates[template.id] = template
        
        return templates
    
    def _load_industry_contexts(self) -> Dict[str, Dict[str, Any]]:
        """Load industry-specific context information"""
        return {
            "landscaping": {
                "service_specialties": "residential landscaping, commercial maintenance, garden design, tree services",
                "service_areas": "lawn care, planting, hardscaping, irrigation, seasonal cleanup",
                "common_services": ["lawn mowing", "garden design", "tree trimming", "irrigation", "hardscaping"],
                "seasonal_context": "spring planting, summer maintenance, fall cleanup, winter preparation"
            },
            "real_estate": {
                "property_types": ["residential", "commercial", "luxury", "investment"],
                "services": ["buying", "selling", "renting", "property management"],
                "market_focus": "local market expertise, neighborhood insights, pricing strategies"
            },
            "healthcare": {
                "service_types": ["primary care", "specialty care", "urgent care", "telemedicine"],
                "appointment_types": ["consultation", "follow-up", "procedure", "emergency"],
                "compliance_focus": "HIPAA compliance, patient privacy, medical records"
            },
            "general": {
                "service_types": ["consultation", "support", "sales", "follow-up"],
                "communication_style": "professional, helpful, responsive"
            }
        }
    
    def get_template(self, template_id: str) -> Optional[EmailTemplate]:
        """Get a specific template by ID"""
        return self.templates.get(template_id)
    
    def get_templates_by_industry(self, industry: str) -> List[EmailTemplate]:
        """Get all templates for a specific industry"""
        return [template for template in self.templates.values() 
                if template.industry == industry and template.is_active]
    
    def get_template_by_intent(self, industry: str, intent: str) -> Optional[EmailTemplate]:
        """Get template by industry and intent"""
        for template in self.templates.values():
            if template.industry == industry and template.intent == intent and template.is_active:
                return template
        return None
    
    def generate_email_content(self, template_id: str, variables: Dict[str, Any]) -> Dict[str, str]:
        """Generate email content from template"""
        template = self.get_template(template_id)
        if not template:
            return {"error": "Template not found"}
        
        try:
            # Get industry context
            industry_context = self.industry_contexts.get(template.industry, {})
            
            # Merge variables with industry context
            merged_variables = {**industry_context, **variables}
            
            # Generate subject
            subject = template.subject_template.format(**merged_variables)
            
            # Generate body
            body = template.body_template.format(**merged_variables)
            
            return {
                "subject": subject,
                "body": body,
                "template_id": template_id,
                "industry": template.industry
            }
            
        except KeyError as e:
            logger.error(f"❌ Missing variable in template {template_id}: {e}")
            return {"error": f"Missing required variable: {e}"}
        except Exception as e:
            logger.error(f"❌ Template generation failed: {e}")
            return {"error": "Template generation failed"}
    
    def create_custom_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a custom email template"""
        try:
            template_id = f"custom_{int(datetime.now().timestamp())}"
            
            template = EmailTemplate(
                id=template_id,
                name=template_data.get('name', 'Custom Template'),
                industry=template_data.get('industry', 'general'),
                intent=template_data.get('intent', 'general'),
                subject_template=template_data.get('subject_template', ''),
                body_template=template_data.get('body_template', ''),
                variables=template_data.get('variables', []),
                is_active=True,
                created_at=datetime.now()
            )
            
            self.templates[template_id] = template
            
            logger.info(f"✅ Custom template created: {template_id}")
            return {"success": True, "template_id": template_id}
            
        except Exception as e:
            logger.error(f"❌ Failed to create custom template: {e}")
            return {"success": False, "error": str(e)}
    
    def get_available_industries(self) -> List[str]:
        """Get list of available industries"""
        industries = set()
        for template in self.templates.values():
            industries.add(template.industry)
        return list(industries)
    
    def get_template_statistics(self) -> Dict[str, Any]:
        """Get template usage statistics"""
        stats = {
            "total_templates": len(self.templates),
            "active_templates": len([t for t in self.templates.values() if t.is_active]),
            "industries": len(self.get_available_industries()),
            "templates_by_industry": {}
        }
        
        for industry in self.get_available_industries():
            industry_templates = self.get_templates_by_industry(industry)
            stats["templates_by_industry"][industry] = len(industry_templates)
        
        return stats

# Global instance
email_templates = None

def get_email_templates() -> AdvancedEmailTemplates:
    """Get the global email templates instance"""
    global email_templates
    
    if email_templates is None:
        email_templates = AdvancedEmailTemplates()
    
    return email_templates
