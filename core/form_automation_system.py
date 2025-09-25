"""
Form Automation System for Fikiri Solutions
Handles dynamic form generation, validation, and processing
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import uuid

from core.minimal_config import get_config

logger = logging.getLogger(__name__)

class FieldType(Enum):
    """Form field types"""
    TEXT = "text"
    EMAIL = "email"
    PHONE = "phone"
    NUMBER = "number"
    DATE = "date"
    SELECT = "select"
    MULTISELECT = "multiselect"
    TEXTAREA = "textarea"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    FILE = "file"
    URL = "url"

class ValidationRule(Enum):
    """Validation rule types"""
    REQUIRED = "required"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    EMAIL_FORMAT = "email_format"
    PHONE_FORMAT = "phone_format"
    URL_FORMAT = "url_format"
    NUMBER_RANGE = "number_range"
    DATE_RANGE = "date_range"
    CUSTOM_REGEX = "custom_regex"

@dataclass
class FormField:
    """Form field definition"""
    id: str
    name: str
    label: str
    field_type: FieldType
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    required: bool = False
    validation_rules: List[Dict[str, Any]] = None
    options: List[Dict[str, str]] = None  # For select/radio fields
    default_value: Optional[str] = None
    order: int = 0

@dataclass
class FormTemplate:
    """Form template definition"""
    id: str
    name: str
    description: str
    industry: str
    purpose: str
    fields: List[FormField]
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

@dataclass
class FormSubmission:
    """Form submission data"""
    id: str
    form_id: str
    user_id: int
    data: Dict[str, Any]
    submitted_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    validation_errors: List[str] = None

@dataclass
class ValidationResult:
    """Form validation result"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class FormAutomationSystem:
    """Form automation and management system"""
    
    def __init__(self):
        self.config = get_config()
        self.form_templates = self._load_default_templates()
        self.submissions = {}  # In-memory storage for demo
        
        logger.info("📝 Form automation system initialized")
    
    def _load_default_templates(self) -> Dict[str, FormTemplate]:
        """Load default form templates"""
        templates = {}
        
        # Landscaping Quote Request Form
        landscaping_fields = [
            FormField(
                id="contact_name",
                name="contact_name",
                label="Full Name",
                field_type=FieldType.TEXT,
                placeholder="Enter your full name",
                required=True,
                validation_rules=[{"type": "required"}, {"type": "min_length", "value": 2}],
                order=1
            ),
            FormField(
                id="email",
                name="email",
                label="Email Address",
                field_type=FieldType.EMAIL,
                placeholder="your@email.com",
                required=True,
                validation_rules=[{"type": "required"}, {"type": "email_format"}],
                order=2
            ),
            FormField(
                id="phone",
                name="phone",
                label="Phone Number",
                field_type=FieldType.PHONE,
                placeholder="(555) 123-4567",
                required=True,
                validation_rules=[{"type": "required"}, {"type": "phone_format"}],
                order=3
            ),
            FormField(
                id="property_address",
                name="property_address",
                label="Property Address",
                field_type=FieldType.TEXTAREA,
                placeholder="Enter your property address",
                required=True,
                validation_rules=[{"type": "required"}],
                order=4
            ),
            FormField(
                id="service_type",
                name="service_type",
                label="Service Type",
                field_type=FieldType.SELECT,
                required=True,
                options=[
                    {"value": "residential", "label": "Residential Landscaping"},
                    {"value": "commercial", "label": "Commercial Landscaping"},
                    {"value": "maintenance", "label": "Lawn Maintenance"},
                    {"value": "design", "label": "Landscape Design"},
                    {"value": "hardscaping", "label": "Hardscaping"}
                ],
                validation_rules=[{"type": "required"}],
                order=5
            ),
            FormField(
                id="property_size",
                name="property_size",
                label="Property Size (sq ft)",
                field_type=FieldType.NUMBER,
                placeholder="5000",
                help_text="Approximate square footage of your property",
                validation_rules=[{"type": "number_range", "min": 100, "max": 100000}],
                order=6
            ),
            FormField(
                id="budget_range",
                name="budget_range",
                label="Budget Range",
                field_type=FieldType.SELECT,
                options=[
                    {"value": "under_5k", "label": "Under $5,000"},
                    {"value": "5k_10k", "label": "$5,000 - $10,000"},
                    {"value": "10k_25k", "label": "$10,000 - $25,000"},
                    {"value": "25k_50k", "label": "$25,000 - $50,000"},
                    {"value": "over_50k", "label": "Over $50,000"}
                ],
                order=7
            ),
            FormField(
                id="timeline",
                name="timeline",
                label="Project Timeline",
                field_type=FieldType.SELECT,
                options=[
                    {"value": "asap", "label": "ASAP"},
                    {"value": "1_month", "label": "Within 1 month"},
                    {"value": "3_months", "label": "Within 3 months"},
                    {"value": "6_months", "label": "Within 6 months"},
                    {"value": "flexible", "label": "Flexible"}
                ],
                order=8
            ),
            FormField(
                id="project_description",
                name="project_description",
                label="Project Description",
                field_type=FieldType.TEXTAREA,
                placeholder="Describe your landscaping project in detail...",
                help_text="Include any specific requirements, preferences, or challenges",
                order=9
            ),
            FormField(
                id="newsletter_signup",
                name="newsletter_signup",
                label="Subscribe to Newsletter",
                field_type=FieldType.CHECKBOX,
                default_value="false",
                order=10
            )
        ]
        
        templates["landscaping_quote"] = FormTemplate(
            id="landscaping_quote",
            name="Landscaping Quote Request",
            description="Professional landscaping quote request form",
            industry="landscaping",
            purpose="lead_generation",
            fields=landscaping_fields,
            settings={
                "submit_button_text": "Request Quote",
                "success_message": "Thank you! We'll contact you within 24 hours.",
                "redirect_url": "/thank-you",
                "email_notifications": True,
                "auto_respond": True
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Contact Form Template
        contact_fields = [
            FormField(
                id="name",
                name="name",
                label="Name",
                field_type=FieldType.TEXT,
                required=True,
                validation_rules=[{"type": "required"}],
                order=1
            ),
            FormField(
                id="email",
                name="email",
                label="Email",
                field_type=FieldType.EMAIL,
                required=True,
                validation_rules=[{"type": "required"}, {"type": "email_format"}],
                order=2
            ),
            FormField(
                id="subject",
                name="subject",
                label="Subject",
                field_type=FieldType.TEXT,
                required=True,
                validation_rules=[{"type": "required"}],
                order=3
            ),
            FormField(
                id="message",
                name="message",
                label="Message",
                field_type=FieldType.TEXTAREA,
                required=True,
                validation_rules=[{"type": "required"}, {"type": "min_length", "value": 10}],
                order=4
            )
        ]
        
        templates["contact_form"] = FormTemplate(
            id="contact_form",
            name="Contact Form",
            description="General contact form",
            industry="general",
            purpose="contact",
            fields=contact_fields,
            settings={
                "submit_button_text": "Send Message",
                "success_message": "Thank you for your message!",
                "email_notifications": True
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Event Registration Form
        event_fields = [
            FormField(
                id="attendee_name",
                name="attendee_name",
                label="Attendee Name",
                field_type=FieldType.TEXT,
                required=True,
                validation_rules=[{"type": "required"}],
                order=1
            ),
            FormField(
                id="email",
                name="email",
                label="Email Address",
                field_type=FieldType.EMAIL,
                required=True,
                validation_rules=[{"type": "required"}, {"type": "email_format"}],
                order=2
            ),
            FormField(
                id="phone",
                name="phone",
                label="Phone Number",
                field_type=FieldType.PHONE,
                validation_rules=[{"type": "phone_format"}],
                order=3
            ),
            FormField(
                id="company",
                name="company",
                label="Company",
                field_type=FieldType.TEXT,
                order=4
            ),
            FormField(
                id="dietary_restrictions",
                name="dietary_restrictions",
                label="Dietary Restrictions",
                field_type=FieldType.TEXTAREA,
                placeholder="Please list any dietary restrictions or allergies",
                order=5
            ),
            FormField(
                id="emergency_contact",
                name="emergency_contact",
                label="Emergency Contact",
                field_type=FieldType.TEXT,
                help_text="Name and phone number of emergency contact",
                order=6
            )
        ]
        
        templates["event_registration"] = FormTemplate(
            id="event_registration",
            name="Event Registration",
            description="Event registration form",
            industry="events",
            purpose="registration",
            fields=event_fields,
            settings={
                "submit_button_text": "Register",
                "success_message": "Registration successful!",
                "email_notifications": True,
                "confirmation_email": True
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        return templates
    
    def create_form_template(self, template_data: Dict[str, Any]) -> FormTemplate:
        """Create a new form template"""
        try:
            template_id = template_data.get('id', str(uuid.uuid4()))
            
            # Convert field data to FormField objects
            fields = []
            for field_data in template_data.get('fields', []):
                field = FormField(
                    id=field_data['id'],
                    name=field_data['name'],
                    label=field_data['label'],
                    field_type=FieldType(field_data['field_type']),
                    placeholder=field_data.get('placeholder'),
                    help_text=field_data.get('help_text'),
                    required=field_data.get('required', False),
                    validation_rules=field_data.get('validation_rules', []),
                    options=field_data.get('options'),
                    default_value=field_data.get('default_value'),
                    order=field_data.get('order', 0)
                )
                fields.append(field)
            
            template = FormTemplate(
                id=template_id,
                name=template_data['name'],
                description=template_data.get('description', ''),
                industry=template_data.get('industry', 'general'),
                purpose=template_data.get('purpose', 'general'),
                fields=fields,
                settings=template_data.get('settings', {}),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.form_templates[template_id] = template
            logger.info(f"✅ Created form template: {template_id}")
            
            return template
            
        except Exception as e:
            logger.error(f"❌ Failed to create form template: {e}")
            raise
    
    def get_form_template(self, template_id: str) -> Optional[FormTemplate]:
        """Get form template by ID"""
        return self.form_templates.get(template_id)
    
    def list_form_templates(self, industry: Optional[str] = None) -> List[FormTemplate]:
        """List all form templates, optionally filtered by industry"""
        templates = list(self.form_templates.values())
        
        if industry:
            templates = [t for t in templates if t.industry == industry]
        
        return sorted(templates, key=lambda t: t.created_at, reverse=True)
    
    def generate_form_html(self, template_id: str, form_action: str = "/api/forms/submit") -> str:
        """Generate HTML form from template"""
        template = self.get_form_template(template_id)
        if not template:
            return "<p>Form template not found</p>"
        
        html = f"""
        <form id="form_{template_id}" action="{form_action}" method="POST" class="fikiri-form">
            <input type="hidden" name="form_id" value="{template_id}">
            
            <div class="form-header">
                <h2>{template.name}</h2>
                <p>{template.description}</p>
            </div>
            
            <div class="form-fields">
        """
        
        # Sort fields by order
        sorted_fields = sorted(template.fields, key=lambda f: f.order)
        
        for field in sorted_fields:
            html += self._generate_field_html(field)
        
        html += f"""
            </div>
            
            <div class="form-actions">
                <button type="submit" class="btn btn-primary">
                    {template.settings.get('submit_button_text', 'Submit')}
                </button>
            </div>
        </form>
        
        <script>
            // Form validation
            document.getElementById('form_{template_id}').addEventListener('submit', function(e) {{
                if (!validateForm_{template_id}()) {{
                    e.preventDefault();
                }}
            }});
            
            function validateForm_{template_id}() {{
                let isValid = true;
                const errors = [];
                
                // Add validation logic here
                
                if (errors.length > 0) {{
                    alert('Please fix the following errors:\\n' + errors.join('\\n'));
                    isValid = false;
                }}
                
                return isValid;
            }}
        </script>
        """
        
        return html
    
    def _generate_field_html(self, field: FormField) -> str:
        """Generate HTML for a form field"""
        html = f"""
        <div class="form-field" data-field-id="{field.id}">
            <label for="{field.id}" class="field-label">
                {field.label}
                {f'<span class="required">*</span>' if field.required else ''}
            </label>
        """
        
        if field.help_text:
            html += f'<p class="field-help">{field.help_text}</p>'
        
        # Generate field HTML based on type
        if field.field_type == FieldType.TEXT:
            html += f'''
            <input type="text" 
                   id="{field.id}" 
                   name="{field.name}" 
                   placeholder="{field.placeholder or ''}"
                   value="{field.default_value or ''}"
                   {"required" if field.required else ""}
                   class="form-control">
            '''
        
        elif field.field_type == FieldType.EMAIL:
            html += f'''
            <input type="email" 
                   id="{field.id}" 
                   name="{field.name}" 
                   placeholder="{field.placeholder or ''}"
                   value="{field.default_value or ''}"
                   {"required" if field.required else ""}
                   class="form-control">
            '''
        
        elif field.field_type == FieldType.PHONE:
            html += f'''
            <input type="tel" 
                   id="{field.id}" 
                   name="{field.name}" 
                   placeholder="{field.placeholder or ''}"
                   value="{field.default_value or ''}"
                   {"required" if field.required else ""}
                   class="form-control">
            '''
        
        elif field.field_type == FieldType.TEXTAREA:
            html += f'''
            <textarea id="{field.id}" 
                      name="{field.name}" 
                      placeholder="{field.placeholder or ''}"
                      {"required" if field.required else ""}
                      class="form-control"
                      rows="4">{field.default_value or ''}</textarea>
            '''
        
        elif field.field_type == FieldType.SELECT:
            html += f'''
            <select id="{field.id}" 
                    name="{field.name}" 
                    {"required" if field.required else ""}
                    class="form-control">
                <option value="">Select an option</option>
            '''
            for option in field.options or []:
                selected = "selected" if option['value'] == field.default_value else ""
                html += f'<option value="{option["value"]}" {selected}>{option["label"]}</option>'
            html += '</select>'
        
        elif field.field_type == FieldType.CHECKBOX:
            checked = "checked" if field.default_value == "true" else ""
            html += f'''
            <input type="checkbox" 
                   id="{field.id}" 
                   name="{field.name}" 
                   value="true"
                   {checked}
                   class="form-checkbox">
            '''
        
        html += '</div>'
        return html
    
    def validate_form_submission(self, form_id: str, data: Dict[str, Any]) -> ValidationResult:
        """Validate form submission data"""
        template = self.get_form_template(form_id)
        if not template:
            return ValidationResult(
                is_valid=False,
                errors=["Form template not found"],
                warnings=[]
            )
        
        errors = []
        warnings = []
        
        # Validate each field
        for field in template.fields:
            field_value = data.get(field.name, '')
            
            # Required field validation
            if field.required and not field_value:
                errors.append(f"{field.label} is required")
                continue
            
            # Skip validation for empty optional fields
            if not field_value and not field.required:
                continue
            
            # Apply validation rules
            for rule in field.validation_rules or []:
                rule_type = rule.get('type')
                rule_value = rule.get('value')
                
                if rule_type == 'min_length' and len(str(field_value)) < rule_value:
                    errors.append(f"{field.label} must be at least {rule_value} characters")
                
                elif rule_type == 'max_length' and len(str(field_value)) > rule_value:
                    errors.append(f"{field.label} must be no more than {rule_value} characters")
                
                elif rule_type == 'email_format':
                    import re
                    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    if not re.match(email_pattern, str(field_value)):
                        errors.append(f"{field.label} must be a valid email address")
                
                elif rule_type == 'phone_format':
                    import re
                    phone_pattern = r'^[\+]?[1-9][\d]{0,15}$'
                    if not re.match(phone_pattern, str(field_value).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')):
                        errors.append(f"{field.label} must be a valid phone number")
                
                elif rule_type == 'number_range':
                    try:
                        num_value = float(field_value)
                        if 'min' in rule and num_value < rule['min']:
                            errors.append(f"{field.label} must be at least {rule['min']}")
                        if 'max' in rule and num_value > rule['max']:
                            errors.append(f"{field.label} must be no more than {rule['max']}")
                    except ValueError:
                        errors.append(f"{field.label} must be a valid number")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def submit_form(self, form_id: str, data: Dict[str, Any], user_id: int = 1, 
                   ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Dict[str, Any]:
        """Submit form data"""
        try:
            # Validate submission
            validation_result = self.validate_form_submission(form_id, data)
            
            if not validation_result.is_valid:
                return {
                    "success": False,
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings
                }
            
            # Create submission record
            submission_id = str(uuid.uuid4())
            submission = FormSubmission(
                id=submission_id,
                form_id=form_id,
                user_id=user_id,
                data=data,
                submitted_at=datetime.now(),
                ip_address=ip_address,
                user_agent=user_agent,
                validation_errors=None
            )
            
            # Store submission
            self.submissions[submission_id] = submission
            
            # Get template for settings
            template = self.get_form_template(form_id)
            
            logger.info(f"✅ Form submitted successfully: {submission_id}")
            
            return {
                "success": True,
                "submission_id": submission_id,
                "message": template.settings.get('success_message', 'Form submitted successfully!'),
                "redirect_url": template.settings.get('redirect_url'),
                "warnings": validation_result.warnings
            }
            
        except Exception as e:
            logger.error(f"❌ Form submission failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_form_submissions(self, form_id: str, user_id: Optional[int] = None) -> List[FormSubmission]:
        """Get form submissions"""
        submissions = [s for s in self.submissions.values() if s.form_id == form_id]
        
        if user_id:
            submissions = [s for s in submissions if s.user_id == user_id]
        
        return sorted(submissions, key=lambda s: s.submitted_at, reverse=True)
    
    def get_form_statistics(self, form_id: str) -> Dict[str, Any]:
        """Get form statistics"""
        submissions = self.get_form_submissions(form_id)
        
        if not submissions:
            return {
                "total_submissions": 0,
                "submissions_today": 0,
                "submissions_this_week": 0,
                "submissions_this_month": 0,
                "completion_rate": 0
            }
        
        now = datetime.now()
        today = now.date()
        week_ago = now.replace(day=now.day-7) if now.day > 7 else now.replace(month=now.month-1, day=now.day+23) if now.month > 1 else now.replace(year=now.year-1, month=12, day=now.day+23)
        month_ago = now.replace(month=now.month-1) if now.month > 1 else now.replace(year=now.year-1, month=12)
        
        submissions_today = len([s for s in submissions if s.submitted_at.date() == today])
        submissions_this_week = len([s for s in submissions if s.submitted_at >= week_ago])
        submissions_this_month = len([s for s in submissions if s.submitted_at >= month_ago])
        
        return {
            "total_submissions": len(submissions),
            "submissions_today": submissions_today,
            "submissions_this_week": submissions_this_week,
            "submissions_this_month": submissions_this_month,
            "completion_rate": 1.0  # All submitted forms are complete
        }

# Global instance
form_automation = FormAutomationSystem()

def get_form_automation() -> FormAutomationSystem:
    """Get the global form automation instance"""
    return form_automation
