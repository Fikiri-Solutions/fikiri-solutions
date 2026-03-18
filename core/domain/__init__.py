"""
Canonical domain models (Phase 2a).
Lead, KnowledgeSnippet, ExtractedContact — used by CRM, imports, chatbot retrieval, email extraction.
"""

from core.domain.schemas import (
    LEAD_CANONICAL_FIELDS,
    LEAD_REQUIRED_FOR_CREATE,
    LEAD_UPDATEABLE_FIELDS,
    normalize_lead_payload,
    lead_has_required_for_create,
    KNOWLEDGE_SNIPPET_TYPES,
    knowledge_snippet,
    snippets_to_context_string,
    EXTRACTED_CONTACT_FIELDS,
    normalize_extracted_contact,
    extracted_contact_to_lead_payload,
)

__all__ = [
    "domain_schemas",
    "LEAD_CANONICAL_FIELDS",
    "LEAD_REQUIRED_FOR_CREATE",
    "LEAD_UPDATEABLE_FIELDS",
    "normalize_lead_payload",
    "lead_has_required_for_create",
    "KNOWLEDGE_SNIPPET_TYPES",
    "knowledge_snippet",
    "snippets_to_context_string",
    "EXTRACTED_CONTACT_FIELDS",
    "normalize_extracted_contact",
    "extracted_contact_to_lead_payload",
]

# Backward compat: module access
from core.domain import schemas as domain_schemas
