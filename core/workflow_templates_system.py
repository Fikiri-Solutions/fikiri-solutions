"""
Workflow Templates System
Pre-built, turnkey automation workflows for immediate deployment
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from core.automation_engine import TriggerType, ActionType, AutomationStatus

logger = logging.getLogger(__name__)

class WorkflowCategory(Enum):
    """Workflow template categories"""
    LANDSCAPING = "landscaping"
    RESTAURANT = "restaurant"
    MEDICAL = "medical"
    CONTRACTOR = "contractor"
    GENERAL = "general"
    SALES = "sales"
    SUPPORT = "support"

@dataclass
class WorkflowTemplate:
    """Workflow template data structure"""
    id: str
    name: str
    description: str
    category: WorkflowCategory
    industry: str
    complexity: str  # "simple", "intermediate", "advanced"
    estimated_setup_time: str
    features: List[str]
    trigger: Dict[str, Any]
    actions: List[Dict[str, Any]]
    variables: Dict[str, Any]
    prerequisites: List[str]
    success_metrics: List[str]

class WorkflowTemplatesSystem:
    """System for managing pre-built workflow templates"""
    
    def __init__(self):
        self.templates = self._load_workflow_templates()
    
    def _load_workflow_templates(self) -> List[WorkflowTemplate]:
        """Load all workflow templates"""
        return [
            # LANDSCAPING WORKFLOWS
            WorkflowTemplate(
                id="landscaping_quote_request",
                name="Landscaping Quote Request Automation",
                description="Automatically processes landscaping quote requests, schedules consultations, and sends follow-ups",
                category=WorkflowCategory.LANDSCAPING,
                industry="Landscaping",
                complexity="simple",
                estimated_setup_time="5 minutes",
                features=[
                    "Auto-respond to quote requests",
                    "Schedule consultation calls",
                    "Send property assessment forms",
                    "Follow-up reminders",
                    "Lead scoring based on property size"
                ],
                trigger={
                    "type": TriggerType.EMAIL_RECEIVED.value,
                    "conditions": {
                        "keywords": ["quote", "estimate", "landscaping", "yard", "garden"],
                        "subject_contains": ["quote", "estimate", "landscaping"]
                    }
                },
                actions=[
                    {
                        "type": ActionType.SEND_EMAIL.value,
                        "data": {
                            "template": "landscaping_quote_acknowledgment",
                            "subject": "Thank you for your landscaping inquiry - Next steps"
                        }
                    },
                    {
                        "type": ActionType.CREATE_CALENDAR_EVENT.value,
                        "data": {
                            "title": "Landscaping Consultation",
                            "duration": 60,
                            "description": "Initial consultation call"
                        }
                    },
                    {
                        "type": ActionType.UPDATE_CRM_FIELD.value,
                        "data": {
                            "field_name": "lead_source",
                            "field_value": "website_quote_request"
                        }
                    },
                    {
                        "type": ActionType.SCHEDULE_FOLLOW_UP.value,
                        "data": {
                            "follow_up_type": "email",
                            "follow_up_date": "3 days",
                            "message": "Follow up on landscaping quote request"
                        }
                    }
                ],
                variables={
                    "client_name": "{{lead.name}}",
                    "property_address": "{{lead.address}}",
                    "service_type": "{{extracted.service_type}}",
                    "budget_range": "{{extracted.budget}}"
                },
                prerequisites=[
                    "Gmail connected",
                    "Calendar integration",
                    "Landscaping email templates"
                ],
                success_metrics=[
                    "Quote request response time < 1 hour",
                    "Consultation booking rate > 60%",
                    "Follow-up completion rate > 80%"
                ]
            ),
            
            WorkflowTemplate(
                id="landscaping_seasonal_maintenance",
                name="Seasonal Maintenance Reminders",
                description="Automated seasonal maintenance reminders and service scheduling",
                category=WorkflowCategory.LANDSCAPING,
                industry="Landscaping",
                complexity="intermediate",
                estimated_setup_time="10 minutes",
                features=[
                    "Seasonal service reminders",
                    "Weather-based scheduling",
                    "Service package upsells",
                    "Customer retention campaigns"
                ],
                trigger={
                    "type": TriggerType.TIME_BASED.value,
                    "conditions": {
                        "schedule": "monthly",
                        "season": "spring"
                    }
                },
                actions=[
                    {
                        "type": ActionType.SEND_EMAIL.value,
                        "data": {
                            "template": "spring_maintenance_reminder",
                            "subject": "Spring is here! Time for your landscape maintenance"
                        }
                    },
                    {
                        "type": ActionType.CREATE_TASK.value,
                        "data": {
                            "title": "Follow up on spring maintenance",
                            "due_date": "7 days",
                            "priority": "medium"
                        }
                    }
                ],
                variables={
                    "customer_name": "{{customer.name}}",
                    "last_service_date": "{{customer.last_service}}",
                    "service_package": "{{customer.package}}"
                },
                prerequisites=[
                    "Customer database",
                    "Service history tracking",
                    "Email templates"
                ],
                success_metrics=[
                    "Seasonal reminder open rate > 40%",
                    "Service booking rate > 25%",
                    "Customer retention > 85%"
                ]
            ),
            
            # RESTAURANT WORKFLOWS
            WorkflowTemplate(
                id="restaurant_reservation_management",
                name="Restaurant Reservation Management",
                description="Automated reservation handling, confirmations, and follow-ups",
                category=WorkflowCategory.RESTAURANT,
                industry="Restaurant",
                complexity="simple",
                estimated_setup_time="5 minutes",
                features=[
                    "Auto-confirm reservations",
                    "Send reminder texts",
                    "Handle cancellations",
                    "Upsell specials"
                ],
                trigger={
                    "type": TriggerType.EMAIL_RECEIVED.value,
                    "conditions": {
                        "keywords": ["reservation", "booking", "table", "dinner"],
                        "sender_domain": ["opentable.com", "resy.com"]
                    }
                },
                actions=[
                    {
                        "type": ActionType.SEND_EMAIL.value,
                        "data": {
                            "template": "reservation_confirmation",
                            "subject": "Your reservation is confirmed!"
                        }
                    },
                    {
                        "type": ActionType.SEND_SMS.value,
                        "data": {
                            "message": "Your reservation for {{reservation.date}} at {{reservation.time}} is confirmed. We look forward to seeing you!"
                        }
                    },
                    {
                        "type": ActionType.SCHEDULE_FOLLOW_UP.value,
                        "data": {
                            "follow_up_type": "sms",
                            "follow_up_date": "1 day before",
                            "message": "Reminder: Your reservation is tomorrow at {{reservation.time}}"
                        }
                    }
                ],
                variables={
                    "customer_name": "{{reservation.name}}",
                    "reservation_date": "{{reservation.date}}",
                    "reservation_time": "{{reservation.time}}",
                    "party_size": "{{reservation.party_size}}"
                },
                prerequisites=[
                    "Reservation system integration",
                    "SMS service configured",
                    "Restaurant email templates"
                ],
                success_metrics=[
                    "Reservation confirmation rate > 95%",
                    "No-show rate < 10%",
                    "Customer satisfaction > 4.5/5"
                ]
            ),
            
            # MEDICAL WORKFLOWS
            WorkflowTemplate(
                id="medical_appointment_reminders",
                name="Medical Appointment Reminders",
                description="HIPAA-compliant appointment reminders and follow-ups",
                category=WorkflowCategory.MEDICAL,
                industry="Medical",
                complexity="intermediate",
                estimated_setup_time="15 minutes",
                features=[
                    "HIPAA-compliant reminders",
                    "Appointment confirmations",
                    "Pre-appointment instructions",
                    "Follow-up care reminders"
                ],
                trigger={
                    "type": TriggerType.LEAD_CREATED.value,
                    "conditions": {
                        "lead_type": "appointment"
                    }
                },
                actions=[
                    {
                        "type": ActionType.SEND_EMAIL.value,
                        "data": {
                            "template": "appointment_confirmation",
                            "subject": "Your appointment is confirmed"
                        }
                    },
                    {
                        "type": ActionType.SCHEDULE_FOLLOW_UP.value,
                        "data": {
                            "follow_up_type": "email",
                            "follow_up_date": "24 hours before",
                            "message": "Reminder: Your appointment is tomorrow"
                        }
                    }
                ],
                variables={
                    "patient_name": "{{patient.name}}",
                    "appointment_date": "{{appointment.date}}",
                    "appointment_time": "{{appointment.time}}",
                    "doctor_name": "{{appointment.doctor}}"
                },
                prerequisites=[
                    "HIPAA compliance setup",
                    "Medical email templates",
                    "Appointment system integration"
                ],
                success_metrics=[
                    "Appointment confirmation rate > 90%",
                    "No-show rate < 15%",
                    "Patient satisfaction > 4.0/5"
                ]
            ),
            
            # GENERAL BUSINESS WORKFLOWS
            WorkflowTemplate(
                id="lead_nurturing_sequence",
                name="Lead Nurturing Sequence",
                description="Automated lead nurturing with personalized follow-ups",
                category=WorkflowCategory.GENERAL,
                industry="General Business",
                complexity="intermediate",
                estimated_setup_time="10 minutes",
                features=[
                    "Multi-touch nurturing",
                    "Personalized content",
                    "Lead scoring",
                    "Sales handoff"
                ],
                trigger={
                    "type": TriggerType.LEAD_CREATED.value,
                    "conditions": {
                        "lead_source": "website"
                    }
                },
                actions=[
                    {
                        "type": ActionType.SEND_EMAIL.value,
                        "data": {
                            "template": "welcome_sequence_1",
                            "subject": "Welcome! Here's what to expect"
                        }
                    },
                    {
                        "type": ActionType.SCHEDULE_FOLLOW_UP.value,
                        "data": {
                            "follow_up_type": "email",
                            "follow_up_date": "3 days",
                            "message": "Follow-up with valuable content"
                        }
                    },
                    {
                        "type": ActionType.SCHEDULE_FOLLOW_UP.value,
                        "data": {
                            "follow_up_type": "email",
                            "follow_up_date": "7 days",
                            "message": "Case study and social proof"
                        }
                    }
                ],
                variables={
                    "lead_name": "{{lead.name}}",
                    "company_name": "{{lead.company}}",
                    "industry": "{{lead.industry}}"
                },
                prerequisites=[
                    "Email templates",
                    "Lead scoring setup",
                    "CRM integration"
                ],
                success_metrics=[
                    "Email open rate > 25%",
                    "Click-through rate > 5%",
                    "Lead conversion rate > 15%"
                ]
            ),
            
            # SALES WORKFLOWS
            WorkflowTemplate(
                id="sales_pipeline_automation",
                name="Sales Pipeline Automation",
                description="Automated sales pipeline management with stage-based actions",
                category=WorkflowCategory.SALES,
                industry="Sales",
                complexity="advanced",
                estimated_setup_time="20 minutes",
                features=[
                    "Pipeline stage automation",
                    "Deal progression tracking",
                    "Sales team notifications",
                    "Revenue forecasting"
                ],
                trigger={
                    "type": TriggerType.LEAD_STAGE_CHANGED.value,
                    "conditions": {
                        "new_stage": "qualified"
                    }
                },
                actions=[
                    {
                        "type": ActionType.ASSIGN_TEAM_MEMBER.value,
                        "data": {
                            "team_member_id": "{{sales_rep.id}}",
                            "assignment_type": "owner"
                        }
                    },
                    {
                        "type": ActionType.SEND_EMAIL.value,
                        "data": {
                            "template": "sales_handoff",
                            "subject": "New qualified lead assigned"
                        }
                    },
                    {
                        "type": ActionType.CREATE_TASK.value,
                        "data": {
                            "title": "Initial sales call",
                            "due_date": "2 days",
                            "priority": "high"
                        }
                    }
                ],
                variables={
                    "lead_name": "{{lead.name}}",
                    "company_name": "{{lead.company}}",
                    "deal_value": "{{lead.estimated_value}}",
                    "sales_rep": "{{assigned_rep}}"
                },
                prerequisites=[
                    "Sales team setup",
                    "Pipeline stages configured",
                    "Sales email templates"
                ],
                success_metrics=[
                    "Lead response time < 4 hours",
                    "Qualification rate > 30%",
                    "Deal close rate > 20%"
                ]
            ),
            
            # SUPPORT WORKFLOWS
            WorkflowTemplate(
                id="customer_support_triage",
                name="Customer Support Triage",
                description="Automated support ticket routing and priority assignment",
                category=WorkflowCategory.SUPPORT,
                industry="Customer Support",
                complexity="intermediate",
                estimated_setup_time="15 minutes",
                features=[
                    "Ticket auto-routing",
                    "Priority assignment",
                    "SLA tracking",
                    "Escalation management"
                ],
                trigger={
                    "type": TriggerType.EMAIL_RECEIVED.value,
                    "conditions": {
                        "keywords": ["support", "help", "issue", "problem"],
                        "sender_domain": ["customer_domain"]
                    }
                },
                actions=[
                    {
                        "type": ActionType.SEND_EMAIL.value,
                        "data": {
                            "template": "support_acknowledgment",
                            "subject": "We've received your support request"
                        }
                    },
                    {
                        "type": ActionType.ASSIGN_TEAM_MEMBER.value,
                        "data": {
                            "team_member_id": "{{support_agent.id}}",
                            "assignment_type": "owner"
                        }
                    },
                    {
                        "type": ActionType.CREATE_TASK.value,
                        "data": {
                            "title": "Respond to support ticket",
                            "due_date": "4 hours",
                            "priority": "high"
                        }
                    }
                ],
                variables={
                    "customer_name": "{{customer.name}}",
                    "issue_type": "{{extracted.issue_type}}",
                    "priority": "{{calculated.priority}}",
                    "support_agent": "{{assigned_agent}}"
                },
                prerequisites=[
                    "Support team setup",
                    "SLA configuration",
                    "Support email templates"
                ],
                success_metrics=[
                    "First response time < 4 hours",
                    "Resolution time < 24 hours",
                    "Customer satisfaction > 4.0/5"
                ]
            )
        ]
    
    def get_templates_by_category(self, category: WorkflowCategory) -> List[WorkflowTemplate]:
        """Get templates by category"""
        return [template for template in self.templates if template.category == category]
    
    def get_templates_by_industry(self, industry: str) -> List[WorkflowTemplate]:
        """Get templates by industry"""
        return [template for template in self.templates if template.industry.lower() == industry.lower()]
    
    def get_template_by_id(self, template_id: str) -> Optional[WorkflowTemplate]:
        """Get template by ID"""
        for template in self.templates:
            if template.id == template_id:
                return template
        return None
    
    def get_templates_by_complexity(self, complexity: str) -> List[WorkflowTemplate]:
        """Get templates by complexity level"""
        return [template for template in self.templates if template.complexity == complexity]
    
    def create_automation_from_template(self, template_id: str, user_id: int, customizations: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create automation rule from template"""
        try:
            template = self.get_template_by_id(template_id)
            if not template:
                return {'success': False, 'error': 'Template not found'}
            
            # Apply customizations
            trigger = template.trigger.copy()
            actions = template.actions.copy()
            variables = template.variables.copy()
            
            if customizations:
                # Merge customizations
                if 'trigger' in customizations:
                    trigger.update(customizations['trigger'])
                if 'actions' in customizations:
                    actions.extend(customizations['actions'])
                if 'variables' in customizations:
                    variables.update(customizations['variables'])
            
            # Create automation rule data
            rule_data = {
                'name': template.name,
                'description': template.description,
                'trigger_type': trigger['type'],
                'trigger_conditions': trigger.get('conditions', {}),
                'actions': actions,
                'variables': variables,
                'status': AutomationStatus.ACTIVE.value,
                'template_id': template_id
            }
            
            # Import automation engine
            from core.automation_engine import automation_engine
            
            # Create the automation rule
            result = automation_engine.create_automation_rule(user_id, rule_data)
            
            if result['success']:
                logger.info(f"Created automation from template {template_id} for user {user_id}")
                return {
                    'success': True,
                    'automation_id': result['automation_id'],
                    'template_name': template.name,
                    'estimated_setup_time': template.estimated_setup_time
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error creating automation from template: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_template_statistics(self) -> Dict[str, Any]:
        """Get template statistics"""
        categories = {}
        industries = {}
        complexities = {}
        
        for template in self.templates:
            # Count by category
            cat = template.category.value
            categories[cat] = categories.get(cat, 0) + 1
            
            # Count by industry
            ind = template.industry
            industries[ind] = industries.get(ind, 0) + 1
            
            # Count by complexity
            comp = template.complexity
            complexities[comp] = complexities.get(comp, 0) + 1
        
        return {
            'total_templates': len(self.templates),
            'categories': categories,
            'industries': industries,
            'complexities': complexities
        }
    
    def search_templates(self, query: str) -> List[WorkflowTemplate]:
        """Search templates by name, description, or features"""
        query_lower = query.lower()
        results = []
        
        for template in self.templates:
            # Search in name, description, and features
            if (query_lower in template.name.lower() or
                query_lower in template.description.lower() or
                any(query_lower in feature.lower() for feature in template.features)):
                results.append(template)
        
        return results

# Global workflow templates system instance
workflow_templates_system = WorkflowTemplatesSystem()

# Export the system
__all__ = ['WorkflowTemplatesSystem', 'workflow_templates_system', 'WorkflowTemplate', 'WorkflowCategory']
