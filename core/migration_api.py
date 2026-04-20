"""
Content migration / import center — aggregated capabilities and inventory.

Exposes one authenticated GET that lists supported formats, API paths, and
template inventory so the dashboard Import Center stays aligned with the backend.
"""

import logging
from typing import Any, Dict, List

from flask import Blueprint

from core.ai_document_processor import get_document_processor
from core.api_validation import create_error_response, create_success_response, handle_api_errors
from core.document_templates_system import get_document_templates
from core.form_automation_system import get_form_automation
from core.secure_sessions import get_current_user_id

logger = logging.getLogger(__name__)

migration_bp = Blueprint("migration", __name__, url_prefix="/api/migration")


def _flat_extensions(processor) -> List[str]:
    exts: List[str] = []
    for group in processor.supported_formats.values():
        exts.extend(group)
    return sorted(set(exts))


def _build_sections(
    processor,
    doc_templates,
    form_automation,
) -> Dict[str, Any]:
    templates_list = doc_templates.list_templates()
    forms_list = form_automation.list_form_templates()

    return {
        "knowledge_marketing": {
            "title": "Marketing copy, FAQs, and knowledge",
            "description": (
                "Bring website copy, brochures, and Q&A into the chatbot knowledge base. "
                "You can paste text, upload files for text extraction, or use bulk JSON import."
            ),
            "modes": [
                {
                    "id": "verbatim",
                    "label": "Paste or type content",
                    "notes": "Fastest for short snippets.",
                },
                {
                    "id": "extract",
                    "label": "Upload then edit extracted text",
                    "notes": "Best for PDFs, Word, spreadsheets.",
                },
                {
                    "id": "bulk",
                    "label": "Bulk JSON (API-aligned)",
                    "notes": "For migrations from spreadsheets or CMS exports.",
                },
            ],
            "api": [
                {"method": "POST", "path": "/api/chatbot/knowledge/import", "auth": "session_jwt_or_api_key"},
                {"method": "POST", "path": "/api/chatbot/knowledge/import/bulk", "auth": "session_jwt_or_api_key"},
                {"method": "POST", "path": "/api/chatbot/knowledge/documents", "auth": "session_jwt"},
            ],
            "related_ui_path": "/ai/chatbot-builder",
        },
        "documents": {
            "title": "Contracts, proposals, and generated documents",
            "description": (
                "Extract text from existing files for search and knowledge, or generate new documents "
                "from merge templates (placeholders like {{client_name}})."
            ),
            "supported_file_extensions": _flat_extensions(processor),
            "file_categories": processor.supported_formats,
            "api": [
                {
                    "method": "POST",
                    "path": "/api/docs-forms/documents/process",
                    "auth": "session_jwt",
                    "role": "extract_text",
                },
                {
                    "method": "POST",
                    "path": "/api/workflows/documents/generate",
                    "auth": "session_jwt",
                    "role": "generate_from_template",
                    "notes": "Requires a paid plan; rate limited.",
                },
            ],
            "document_templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "document_type": t.document_type.value,
                    "industry": t.industry,
                    "variable_count": len(t.variables),
                }
                for t in templates_list
            ],
            "related_ui_path": "/automations",
        },
        "forms": {
            "title": "Lead and intake forms",
            "description": (
                "Default form definitions can be listed and embedded. Map fields from your old provider "
                "to these templates or recreate parity in the form builder when available."
            ),
            "api": [
                {"method": "GET", "path": "/api/docs-forms/forms/templates", "auth": "public_or_session"},
                {"method": "GET", "path": "/api/docs-forms/forms/templates/<id>", "auth": "public_or_session"},
                {"method": "GET", "path": "/api/docs-forms/forms/templates/<id>/html", "auth": "public_or_session"},
            ],
            "form_templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "industry": t.industry,
                    "purpose": t.purpose,
                    "field_count": len(t.fields),
                }
                for t in forms_list
            ],
        },
        "contacts": {
            "title": "Contacts and leads",
            "description": "Import a CSV of leads; duplicates are handled with a policy you choose.",
            "csv_requirements": {
                "required_columns": ["email", "name"],
                "optional_columns": ["phone", "source", "company"],
                "max_file_mb": 5,
                "max_rows": 10000,
            },
            "on_duplicate_policies": ["skip", "update", "merge"],
            "api": [
                {"method": "POST", "path": "/api/crm/leads/import/csv", "auth": "session_jwt"},
                {"method": "POST", "path": "/api/crm/leads/import/csv/preview", "auth": "session_jwt"},
                {
                    "method": "POST",
                    "path": "/api/crm/leads/import",
                    "auth": "session_jwt",
                    "notes": "JSON body with leads array.",
                },
            ],
            "related_ui_path": "/crm",
        },
    }


@migration_bp.route("/capabilities", methods=["GET"])
@handle_api_errors
def get_migration_capabilities():
    """Return migration feature map, supported formats, and template inventory."""
    user_id = get_current_user_id()
    if not user_id:
        return create_error_response("Authentication required", 401, "AUTHENTICATION_REQUIRED")

    try:
        processor = get_document_processor()
        doc_templates = get_document_templates()
        form_automation = get_form_automation()
        sections = _build_sections(processor, doc_templates, form_automation)
    except Exception as e:
        logger.exception("migration capabilities failed: %s", e)
        return create_error_response("Could not load migration capabilities", 500, "MIGRATION_CAPABILITIES_ERROR")

    payload = {
        "feature": "content_migration",
        "version": 1,
        "sections": sections,
    }
    return create_success_response(payload, "Migration capabilities loaded")
