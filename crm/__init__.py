"""
CRM Module - Customer Relationship Management
Canonical schema and mutations: crm/service.py (EnhancedCRMService, Lead, LeadActivity).
"""
from .service import enhanced_crm_service, Lead, LeadActivity

__all__ = [
    "enhanced_crm_service",
    "Lead",
    "LeadActivity",
]

