"""
Document Templates System for Fikiri Solutions
Handles contract templates, proposal templates, and document generation
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import uuid
import re

from core.minimal_config import get_config

logger = logging.getLogger(__name__)

class DocumentType(Enum):
    """Document template types"""
    CONTRACT = "contract"
    PROPOSAL = "proposal"
    INVOICE = "invoice"
    QUOTE = "quote"
    AGREEMENT = "agreement"
    LETTER = "letter"
    REPORT = "report"
    PRESENTATION = "presentation"

class TemplateFormat(Enum):
    """Template output formats"""
    HTML = "html"
    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"

@dataclass
class TemplateVariable:
    """Template variable definition"""
    name: str
    label: str
    type: str  # text, number, date, boolean, list
    required: bool = False
    default_value: Optional[str] = None
    description: Optional[str] = None
    options: Optional[List[str]] = None  # For select/dropdown variables

@dataclass
class DocumentTemplate:
    """Document template definition"""
    id: str
    name: str
    description: str
    document_type: DocumentType
    industry: str
    template_content: str
    variables: List[TemplateVariable]
    format: TemplateFormat
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

@dataclass
class GeneratedDocument:
    """Generated document result"""
    id: str
    template_id: str
    user_id: int
    content: str
    variables_used: Dict[str, Any]
    format: TemplateFormat
    generated_at: datetime
    metadata: Dict[str, Any]

class DocumentTemplatesSystem:
    """Document templates and generation system"""
    
    def __init__(self):
        self.config = get_config()
        self.templates = self._load_default_templates()
        self.generated_documents = {}  # In-memory storage for demo
        
        logger.info("📄 Document templates system initialized")
    
    def _load_default_templates(self) -> Dict[str, DocumentTemplate]:
        """Load default document templates"""
        templates = {}
        
        # Landscaping Service Agreement Template
        landscaping_agreement_variables = [
            TemplateVariable("client_name", "Client Name", "text", required=True),
            TemplateVariable("client_address", "Client Address", "text", required=True),
            TemplateVariable("client_phone", "Client Phone", "text", required=True),
            TemplateVariable("client_email", "Client Email", "text", required=True),
            TemplateVariable("company_name", "Company Name", "text", required=True, default_value="Fikiri Solutions"),
            TemplateVariable("company_address", "Company Address", "text", required=True),
            TemplateVariable("company_phone", "Company Phone", "text", required=True),
            TemplateVariable("company_email", "Company Email", "text", required=True),
            TemplateVariable("service_description", "Service Description", "text", required=True),
            TemplateVariable("service_price", "Service Price", "number", required=True),
            TemplateVariable("start_date", "Start Date", "date", required=True),
            TemplateVariable("completion_date", "Expected Completion Date", "date"),
            TemplateVariable("payment_terms", "Payment Terms", "text", default_value="Net 30"),
            TemplateVariable("warranty_period", "Warranty Period", "text", default_value="1 year")
        ]
        
        landscaping_agreement_content = """
# LANDSCAPING SERVICE AGREEMENT

**Agreement Date:** {{current_date}}  
**Agreement Number:** {{agreement_number}}

## PARTIES

**Service Provider:**  
{{company_name}}  
{{company_address}}  
Phone: {{company_phone}}  
Email: {{company_email}}

**Client:**  
{{client_name}}  
{{client_address}}  
Phone: {{client_phone}}  
Email: {{client_email}}

## SERVICE DESCRIPTION

{{company_name}} agrees to provide the following landscaping services:

{{service_description}}

## TERMS AND CONDITIONS

### 1. Scope of Work
The services described above will be performed in a professional manner in accordance with industry standards.

### 2. Timeline
- **Start Date:** {{start_date}}
- **Expected Completion:** {{completion_date}}

### 3. Payment Terms
- **Total Cost:** ${{service_price}}
- **Payment Terms:** {{payment_terms}}
- Payment is due within the specified terms from the date of invoice.

### 4. Warranty
{{company_name}} provides a {{warranty_period}} warranty on all work performed, covering defects in workmanship.

### 5. Changes to Scope
Any changes to the original scope of work must be agreed upon in writing and may result in additional charges.

### 6. Liability
{{company_name}} maintains appropriate insurance coverage. Liability is limited to the contract value.

### 7. Cancellation
Either party may cancel this agreement with 48 hours written notice. Client is responsible for payment of work completed.

## SIGNATURES

**Client Signature:** _________________________ **Date:** _________  
{{client_name}}

**Service Provider Signature:** _________________________ **Date:** _________  
{{company_name}} Representative

---
*This agreement constitutes the entire agreement between the parties and may only be modified in writing.*
        """
        
        templates["landscaping_agreement"] = DocumentTemplate(
            id="landscaping_agreement",
            name="Landscaping Service Agreement",
            description="Professional landscaping service agreement template",
            document_type=DocumentType.CONTRACT,
            industry="landscaping",
            template_content=landscaping_agreement_content.strip(),
            variables=landscaping_agreement_variables,
            format=TemplateFormat.MARKDOWN,
            settings={
                "auto_number": True,
                "include_signature_fields": True,
                "require_client_signature": True
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Business Proposal Template
        proposal_variables = [
            TemplateVariable("client_name", "Client Name", "text", required=True),
            TemplateVariable("client_company", "Client Company", "text", required=True),
            TemplateVariable("project_title", "Project Title", "text", required=True),
            TemplateVariable("project_description", "Project Description", "text", required=True),
            TemplateVariable("project_objectives", "Project Objectives", "text", required=True),
            TemplateVariable("deliverables", "Deliverables", "text", required=True),
            TemplateVariable("timeline", "Project Timeline", "text", required=True),
            TemplateVariable("total_cost", "Total Cost", "number", required=True),
            TemplateVariable("company_name", "Company Name", "text", required=True, default_value="Fikiri Solutions"),
            TemplateVariable("proposal_valid_until", "Proposal Valid Until", "date", required=True)
        ]
        
        proposal_content = """
# BUSINESS PROPOSAL

**Proposal for:** {{client_company}}  
**Attention:** {{client_name}}  
**Date:** {{current_date}}  
**Proposal #:** {{proposal_number}}

---

## EXECUTIVE SUMMARY

We are pleased to present this proposal for **{{project_title}}**. {{company_name}} is committed to delivering exceptional results that exceed your expectations and drive your business forward.

## PROJECT OVERVIEW

### Project Description
{{project_description}}

### Objectives
{{project_objectives}}

### Key Deliverables
{{deliverables}}

## PROJECT TIMELINE

{{timeline}}

## INVESTMENT

**Total Project Cost:** ${{total_cost}}

This investment includes all services, deliverables, and support outlined in this proposal.

## WHY CHOOSE {{company_name}}?

- **Expertise:** Years of experience in delivering successful projects
- **Quality:** Commitment to excellence in every aspect of our work
- **Support:** Dedicated support throughout and after project completion
- **Results:** Track record of delivering measurable results for our clients

## NEXT STEPS

1. **Review:** Please review this proposal carefully
2. **Questions:** Contact us with any questions or clarifications
3. **Approval:** Sign and return to begin the project
4. **Kickoff:** We'll schedule a project kickoff meeting

## TERMS

- This proposal is valid until: **{{proposal_valid_until}}**
- Payment terms: 50% upon signing, 50% upon completion
- Project timeline assumes timely client feedback and approvals

---

**Prepared by:** {{company_name}}  
**Contact:** For questions about this proposal, please contact us immediately.

We look forward to working with you on this exciting project!

**Signature:** ___________________________ **Date:** ___________  
{{company_name}} Representative
        """
        
        templates["business_proposal"] = DocumentTemplate(
            id="business_proposal",
            name="Business Proposal",
            description="Professional business proposal template",
            document_type=DocumentType.PROPOSAL,
            industry="general",
            template_content=proposal_content.strip(),
            variables=proposal_variables,
            format=TemplateFormat.MARKDOWN,
            settings={
                "auto_number": True,
                "include_cover_page": True,
                "include_terms": True
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Invoice Template
        invoice_variables = [
            TemplateVariable("client_name", "Client Name", "text", required=True),
            TemplateVariable("client_address", "Client Address", "text", required=True),
            TemplateVariable("client_email", "Client Email", "text"),
            TemplateVariable("service_description", "Service Description", "text", required=True),
            TemplateVariable("quantity", "Quantity", "number", default_value="1"),
            TemplateVariable("unit_price", "Unit Price", "number", required=True),
            TemplateVariable("tax_rate", "Tax Rate (%)", "number", default_value="0"),
            TemplateVariable("payment_terms", "Payment Terms", "text", default_value="Net 30"),
            TemplateVariable("company_name", "Company Name", "text", required=True, default_value="Fikiri Solutions"),
            TemplateVariable("company_address", "Company Address", "text", required=True),
            TemplateVariable("company_phone", "Company Phone", "text"),
            TemplateVariable("company_email", "Company Email", "text")
        ]
        
        invoice_content = """
# INVOICE

**{{company_name}}**  
{{company_address}}  
Phone: {{company_phone}}  
Email: {{company_email}}

---

**Invoice #:** {{invoice_number}}  
**Date:** {{current_date}}  
**Due Date:** {{due_date}}

**Bill To:**  
{{client_name}}  
{{client_address}}  
{{client_email}}

---

## SERVICES

| Description | Quantity | Unit Price | Total |
|-------------|----------|------------|-------|
| {{service_description}} | {{quantity}} | ${{unit_price}} | ${{subtotal}} |

---

**Subtotal:** ${{subtotal}}  
**Tax ({{tax_rate}}%):** ${{tax_amount}}  
**Total Amount:** ${{total_amount}}

---

## PAYMENT INFORMATION

**Payment Terms:** {{payment_terms}}  
**Amount Due:** ${{total_amount}}

Please remit payment by the due date shown above. Thank you for your business!

---

*Questions about this invoice? Contact us at {{company_email}}*
        """
        
        templates["invoice"] = DocumentTemplate(
            id="invoice",
            name="Professional Invoice",
            description="Professional invoice template with automatic calculations",
            document_type=DocumentType.INVOICE,
            industry="general",
            template_content=invoice_content.strip(),
            variables=invoice_variables,
            format=TemplateFormat.MARKDOWN,
            settings={
                "auto_number": True,
                "auto_calculate": True,
                "include_payment_terms": True
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        return templates
    
    def create_template(self, template_data: Dict[str, Any]) -> DocumentTemplate:
        """Create a new document template"""
        try:
            template_id = template_data.get('id', str(uuid.uuid4()))
            
            # Convert variable data to TemplateVariable objects
            variables = []
            for var_data in template_data.get('variables', []):
                variable = TemplateVariable(
                    name=var_data['name'],
                    label=var_data['label'],
                    type=var_data['type'],
                    required=var_data.get('required', False),
                    default_value=var_data.get('default_value'),
                    description=var_data.get('description'),
                    options=var_data.get('options')
                )
                variables.append(variable)
            
            template = DocumentTemplate(
                id=template_id,
                name=template_data['name'],
                description=template_data.get('description', ''),
                document_type=DocumentType(template_data['document_type']),
                industry=template_data.get('industry', 'general'),
                template_content=template_data['template_content'],
                variables=variables,
                format=TemplateFormat(template_data.get('format', 'markdown')),
                settings=template_data.get('settings', {}),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.templates[template_id] = template
            logger.info(f"✅ Created document template: {template_id}")
            
            return template
            
        except Exception as e:
            logger.error(f"❌ Failed to create document template: {e}")
            raise
    
    def get_template(self, template_id: str) -> Optional[DocumentTemplate]:
        """Get document template by ID"""
        return self.templates.get(template_id)
    
    def list_templates(self, document_type: Optional[DocumentType] = None, 
                      industry: Optional[str] = None) -> List[DocumentTemplate]:
        """List document templates with optional filtering"""
        templates = [t for t in self.templates.values() if t.is_active]
        
        if document_type:
            templates = [t for t in templates if t.document_type == document_type]
        
        if industry:
            templates = [t for t in templates if t.industry == industry]
        
        return sorted(templates, key=lambda t: t.created_at, reverse=True)
    
    def generate_document(self, template_id: str, variables: Dict[str, Any], 
                         user_id: int = 1) -> GeneratedDocument:
        """Generate document from template"""
        try:
            template = self.get_template(template_id)
            if not template:
                raise ValueError(f"Template not found: {template_id}")
            
            # Add automatic variables
            auto_variables = self._generate_automatic_variables(template, variables)
            all_variables = {**variables, **auto_variables}
            
            # Validate required variables
            missing_vars = []
            for var in template.variables:
                if var.required and var.name not in all_variables:
                    missing_vars.append(var.name)
            
            if missing_vars:
                raise ValueError(f"Missing required variables: {', '.join(missing_vars)}")
            
            # Apply default values for missing optional variables
            for var in template.variables:
                if var.name not in all_variables and var.default_value:
                    all_variables[var.name] = var.default_value
            
            # Process template content
            content = self._process_template_content(template.template_content, all_variables)
            
            # Create generated document record
            doc_id = str(uuid.uuid4())
            generated_doc = GeneratedDocument(
                id=doc_id,
                template_id=template_id,
                user_id=user_id,
                content=content,
                variables_used=all_variables,
                format=template.format,
                generated_at=datetime.now(),
                metadata={
                    "template_name": template.name,
                    "document_type": template.document_type.value,
                    "industry": template.industry
                }
            )
            
            # Store generated document
            self.generated_documents[doc_id] = generated_doc
            
            logger.info(f"✅ Generated document: {doc_id} from template: {template_id}")
            
            return generated_doc
            
        except Exception as e:
            logger.error(f"❌ Document generation failed: {e}")
            raise
    
    def _generate_automatic_variables(self, template: DocumentTemplate, 
                                    user_variables: Dict[str, Any]) -> Dict[str, Any]:
        """Generate automatic variables like dates, numbers, etc."""
        auto_vars = {}
        
        # Current date
        auto_vars['current_date'] = datetime.now().strftime('%B %d, %Y')
        auto_vars['current_date_short'] = datetime.now().strftime('%m/%d/%Y')
        
        # Auto-numbering
        if template.settings.get('auto_number'):
            if template.document_type == DocumentType.INVOICE:
                auto_vars['invoice_number'] = f"INV-{datetime.now().strftime('%Y%m%d')}-{len(self.generated_documents) + 1:04d}"
            elif template.document_type == DocumentType.PROPOSAL:
                auto_vars['proposal_number'] = f"PROP-{datetime.now().strftime('%Y%m%d')}-{len(self.generated_documents) + 1:04d}"
            elif template.document_type == DocumentType.CONTRACT:
                auto_vars['agreement_number'] = f"AGR-{datetime.now().strftime('%Y%m%d')}-{len(self.generated_documents) + 1:04d}"
        
        # Auto-calculations for invoices
        if template.document_type == DocumentType.INVOICE and template.settings.get('auto_calculate'):
            quantity = float(user_variables.get('quantity', 1))
            unit_price = float(user_variables.get('unit_price', 0))
            tax_rate = float(user_variables.get('tax_rate', 0)) / 100
            
            subtotal = quantity * unit_price
            tax_amount = subtotal * tax_rate
            total_amount = subtotal + tax_amount
            
            auto_vars['subtotal'] = f"{subtotal:.2f}"
            auto_vars['tax_amount'] = f"{tax_amount:.2f}"
            auto_vars['total_amount'] = f"{total_amount:.2f}"
            
            # Calculate due date
            payment_terms = user_variables.get('payment_terms', 'Net 30')
            if 'Net' in payment_terms:
                days = int(re.findall(r'\d+', payment_terms)[0])
                from datetime import timedelta
                due_date = datetime.now() + timedelta(days=days)
                auto_vars['due_date'] = due_date.strftime('%B %d, %Y')
        
        return auto_vars
    
    def _process_template_content(self, content: str, variables: Dict[str, Any]) -> str:
        """Process template content by replacing variables"""
        processed_content = content
        
        # Replace variables in {{variable_name}} format
        for var_name, var_value in variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            processed_content = processed_content.replace(placeholder, str(var_value))
        
        # Clean up any remaining placeholders
        remaining_placeholders = re.findall(r'\{\{([^}]+)\}\}', processed_content)
        for placeholder in remaining_placeholders:
            processed_content = processed_content.replace(f"{{{{{placeholder}}}}}", f"[{placeholder}]")
        
        return processed_content
    
    def get_generated_document(self, doc_id: str) -> Optional[GeneratedDocument]:
        """Get generated document by ID"""
        return self.generated_documents.get(doc_id)
    
    def list_generated_documents(self, user_id: Optional[int] = None, 
                               template_id: Optional[str] = None) -> List[GeneratedDocument]:
        """List generated documents with optional filtering"""
        documents = list(self.generated_documents.values())
        
        if user_id:
            documents = [d for d in documents if d.user_id == user_id]
        
        if template_id:
            documents = [d for d in documents if d.template_id == template_id]
        
        return sorted(documents, key=lambda d: d.generated_at, reverse=True)
    
    def convert_document_format(self, doc_id: str, target_format: TemplateFormat) -> str:
        """Convert document to different format"""
        document = self.get_generated_document(doc_id)
        if not document:
            raise ValueError(f"Document not found: {doc_id}")
        
        # Basic format conversion (simplified)
        content = document.content
        
        if target_format == TemplateFormat.HTML:
            # Convert Markdown to HTML (basic)
            content = content.replace('\n# ', '\n<h1>').replace('# ', '<h1>')
            content = content.replace('\n## ', '\n<h2>').replace('## ', '<h2>')
            content = content.replace('\n### ', '\n<h3>').replace('### ', '<h3>')
            content = content.replace('**', '<strong>').replace('**', '</strong>')
            content = content.replace('\n\n', '</p>\n<p>')
            content = f"<html><body><p>{content}</p></body></html>"
        
        elif target_format == TemplateFormat.TXT:
            # Strip markdown formatting
            content = re.sub(r'#+\s*', '', content)
            content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
            content = re.sub(r'\|(.*?)\|', r'\1', content)
        
        return content
    
    def get_template_statistics(self) -> Dict[str, Any]:
        """Get template usage statistics"""
        total_templates = len(self.templates)
        total_generated = len(self.generated_documents)
        
        # Count by document type
        type_counts = {}
        for template in self.templates.values():
            doc_type = template.document_type.value
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        
        # Count by industry
        industry_counts = {}
        for template in self.templates.values():
            industry = template.industry
            industry_counts[industry] = industry_counts.get(industry, 0) + 1
        
        return {
            "total_templates": total_templates,
            "total_generated_documents": total_generated,
            "templates_by_type": type_counts,
            "templates_by_industry": industry_counts,
            "most_used_template": max(self.templates.keys(), key=lambda t: len([d for d in self.generated_documents.values() if d.template_id == t])) if self.generated_documents else None
        }

# Global instance
document_templates = DocumentTemplatesSystem()

def get_document_templates() -> DocumentTemplatesSystem:
    """Get the global document templates instance"""
    return document_templates
