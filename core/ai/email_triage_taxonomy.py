"""Inbox Command Center categories, cleanup actions, and tab mapping."""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, List, Optional, Tuple

# Primary triage buckets (Inbox Command Center)
TRIAGE_CATEGORIES: Tuple[str, ...] = (
    "business_lead",
    "existing_client",
    "action_needed",
    "vendor_partner",
    "newsletter_marketing",
    "spam_risk",
    "personal_non_business",
    "review_needed",
)

TRIAGE_CATEGORY_SET: FrozenSet[str] = frozenset(TRIAGE_CATEGORIES)

CLEANUP_ACTIONS: Tuple[str, ...] = (
    "keep",
    "archive",
    "label",
    "delete_candidate",
    "spam_candidate",
)

CLEANUP_ACTION_SET: FrozenSet[str] = frozenset(CLEANUP_ACTIONS)

# UI tabs (category filter values)
INBOX_COMMAND_CENTER_TABS: Tuple[Dict[str, str], ...] = (
    {"id": "business_lead", "label": "Leads"},
    {"id": "action_needed", "label": "Action Needed"},
    {"id": "existing_client", "label": "Clients"},
    {"id": "vendor_partner", "label": "Vendors"},
    {"id": "newsletter_marketing", "label": "Marketing/Newsletters"},
    {"id": "spam_risk", "label": "Spam/Risk"},
    {"id": "personal_non_business", "label": "Personal/Non-Business"},
    {"id": "review_needed", "label": "Review Queue"},
)

DESTRUCTIVE_CLEANUP_ACTIONS: FrozenSet[str] = frozenset({"delete_candidate", "spam_candidate"})

# Canonical intent → triage category
INTENT_TO_TRIAGE_CATEGORY: Dict[str, str] = {
    "new_lead": "business_lead",
    "service_inquiry": "business_lead",
    "sales_opportunity": "business_lead",
    "pricing_request": "business_lead",
    "consultation_request": "business_lead",
    "partnership_request": "vendor_partner",
    "job_or_career_inquiry": "review_needed",
    "vendor_or_supplier_offer": "vendor_partner",
    "existing_customer_support": "action_needed",
    "complaint_or_escalation": "action_needed",
    "meeting_or_scheduling_request": "action_needed",
    "follow_up_required": "action_needed",
    "invoice_or_payment_related": "existing_client",
    "contract_or_legal_related": "review_needed",
    "spam_or_low_value": "spam_risk",
    "newsletter_or_marketing": "newsletter_marketing",
    "unknown_business_relevant": "review_needed",
    "not_business_relevant": "personal_non_business",
}


def normalize_triage_category(raw: Any, *, default: str = "review_needed") -> str:
    if raw is None:
        return default
    key = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "lead": "business_lead",
        "leads": "business_lead",
        "client": "existing_client",
        "clients": "existing_client",
        "customer": "existing_client",
        "support": "action_needed",
        "action": "action_needed",
        "vendor": "vendor_partner",
        "partner": "vendor_partner",
        "marketing": "newsletter_marketing",
        "newsletter": "newsletter_marketing",
        "spam": "spam_risk",
        "scam": "spam_risk",
        "personal": "personal_non_business",
        "non_business": "personal_non_business",
        "unknown": "review_needed",
        "review": "review_needed",
    }
    key = aliases.get(key, key)
    return key if key in TRIAGE_CATEGORY_SET else default


def normalize_cleanup_action(raw: Any, *, default: str = "keep") -> str:
    if raw is None:
        return default
    key = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    if key in CLEANUP_ACTION_SET:
        return key
    if key in ("spam", "report_spam"):
        return "spam_candidate"
    if key in ("delete", "trash"):
        return "delete_candidate"
    return default


def category_from_intent(intent: str) -> str:
    from core.ai.email_intent_taxonomy import normalize_intent

    canon = normalize_intent(intent)
    return INTENT_TO_TRIAGE_CATEGORY.get(canon, "review_needed")


def default_cleanup_for_category(category: str, *, lead_score: int = 0) -> str:
    cat = normalize_triage_category(category)
    if cat == "spam_risk":
        return "spam_candidate"
    if cat == "newsletter_marketing":
        return "archive"
    if cat == "personal_non_business":
        return "archive"
    if cat == "business_lead" and lead_score >= 60:
        return "keep"
    if cat == "review_needed":
        return "label"
    if cat in ("action_needed", "existing_client", "vendor_partner"):
        return "keep"
    return "keep"


def suggested_gmail_labels(category: str, cleanup_action: str) -> List[str]:
    """Human-readable label names for bulk label action (Gmail label ids resolved separately)."""
    cat = normalize_triage_category(category)
    labels = [f"Fikiri/{cat}"]
    if cleanup_action == "spam_candidate":
        labels.append("Fikiri/spam_candidate")
    if cleanup_action == "delete_candidate":
        labels.append("Fikiri/delete_candidate")
    return labels
