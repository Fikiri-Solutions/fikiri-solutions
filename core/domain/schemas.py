#!/usr/bin/env python3
"""
Canonical domain schemas (Phase 2a).
Lead, KnowledgeSnippet, ExtractedContact — for CRM, imports, chatbot retrieval, email extraction.
Not AI-only; used across integrations and exports.
"""

from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# Lead (aligned with crm/service.py: create_lead, update_lead, leads table)
# ---------------------------------------------------------------------------

LEAD_CANONICAL_FIELDS = [
    "id", "user_id", "email", "name", "phone", "company", "source", "stage",
    "score", "created_at", "updated_at", "last_contact", "notes", "tags", "metadata",
]

LEAD_REQUIRED_FOR_CREATE = ("email", "name")

LEAD_UPDATEABLE_FIELDS = ("name", "phone", "company", "source", "stage", "notes", "tags", "metadata")


def normalize_lead_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a dict with only canonical lead keys. Does not set defaults; use for validation/whitelist before create_lead."""
    return {k: v for k, v in data.items() if k in LEAD_CANONICAL_FIELDS}


def lead_has_required_for_create(data: Dict[str, Any]) -> bool:
    """True if data has email and name (non-empty)."""
    return bool((data.get("email") or "").strip() and (data.get("name") or "").strip())


# ---------------------------------------------------------------------------
# KnowledgeSnippet (chatbot retrieval: FAQ, KB, vector — align with _build_sources / _build_context_snippets)
# ---------------------------------------------------------------------------

KNOWLEDGE_SNIPPET_TYPES = ("faq", "knowledge_base", "vector")


def knowledge_snippet(
    type: str,
    content: str,
    title: Optional[str] = None,
    question: Optional[str] = None,
    answer: Optional[str] = None,
    source_id: Optional[str] = None,
    relevance: Optional[float] = None,
    confidence: Optional[float] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """Build a canonical KnowledgeSnippet. type must be faq | knowledge_base | vector."""
    out: Dict[str, Any] = {"type": type, "content": content}
    if title is not None:
        out["title"] = title
    if question is not None:
        out["question"] = question
    if answer is not None:
        out["answer"] = answer
    if source_id is not None:
        out["source_id"] = source_id
    if relevance is not None:
        out["relevance"] = relevance
    if confidence is not None:
        out["confidence"] = confidence
    for k, v in extra.items():
        if k not in out:
            out[k] = v
    return out


def snippets_to_context_string(snippets: List[Dict[str, Any]]) -> str:
    """Turn list of KnowledgeSnippet-like dicts into one string for LLM prompt context."""
    lines = []
    for s in snippets:
        t = s.get("type", "")
        if t == "faq":
            lines.append(f"FAQ: Q={s.get('question', '')} A={s.get('answer', '')}")
        elif t == "knowledge_base":
            lines.append(f"KB: {s.get('title', '')}: {s.get('content', '')}")
        elif t == "vector":
            lines.append(f"KB: {s.get('content', '')}")
        else:
            lines.append(s.get("content", ""))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ExtractedContact (email contact extraction — align with ai_assistant CONTACT_SCHEMA for LLM output)
# ---------------------------------------------------------------------------

EXTRACTED_CONTACT_FIELDS = (
    "phone", "company", "website", "location", "budget", "timeline", "email", "name",
)


def normalize_extracted_contact(data: Dict[str, Any]) -> Dict[str, Any]:
    """Return dict with only ExtractedContact fields. All keys optional; use for merge into Lead."""
    return {k: v for k, v in data.items() if k in EXTRACTED_CONTACT_FIELDS}


def extracted_contact_to_lead_payload(contact: Dict[str, Any], default_source: str = "email") -> Dict[str, Any]:
    """Convert ExtractedContact to a payload suitable for create_lead. email/name from contact or placeholder."""
    out = normalize_extracted_contact(contact)
    email = (out.get("email") or "").strip()
    name = (out.get("name") or "").strip()
    if not name and email:
        name = email.split("@")[0] if "@" in email else email
    if not email:
        email = "unknown@unknown"
    if not name:
        name = "Unknown"
    out["email"] = email
    out["name"] = name
    out.setdefault("source", default_source)
    return out
