"""
Canonical business email intent taxonomy for Fikiri AI Email Assistant.

Extend by adding IDs here, updating LEGACY_INTENT_MAP aliases, and
BusinessEmailAnalysisV2Schema in core/ai/schemas.py.
"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, List, Optional, Tuple

# Primary business intent categories (stable snake_case IDs)
PRIMARY_EMAIL_INTENTS: Tuple[str, ...] = (
    "new_lead",
    "service_inquiry",
    "sales_opportunity",
    "pricing_request",
    "consultation_request",
    "partnership_request",
    "job_or_career_inquiry",
    "vendor_or_supplier_offer",
    "existing_customer_support",
    "complaint_or_escalation",
    "meeting_or_scheduling_request",
    "follow_up_required",
    "invoice_or_payment_related",
    "contract_or_legal_related",
    "spam_or_low_value",
    "newsletter_or_marketing",
    "unknown_business_relevant",
    "not_business_relevant",
)

PRIMARY_INTENT_SET: FrozenSet[str] = frozenset(PRIMARY_EMAIL_INTENTS)

# Legacy intents still returned by older prompts/fallbacks
LEGACY_INTENTS: FrozenSet[str] = frozenset(
    {
        "lead_inquiry",
        "support_request",
        "general_info",
        "complaint",
        "spam",
        "scheduling",
        "escalation",
        "legal",
        "billing_dispute",
    }
)

# Map legacy / alias strings -> canonical primary intent
LEGACY_INTENT_MAP: Dict[str, str] = {
    "lead_inquiry": "new_lead",
    "lead": "new_lead",
    "inquiry": "service_inquiry",
    "general_info": "unknown_business_relevant",
    "general": "unknown_business_relevant",
    "support_request": "existing_customer_support",
    "support": "existing_customer_support",
    "complaint": "complaint_or_escalation",
    "escalation": "complaint_or_escalation",
    "spam": "spam_or_low_value",
    "scheduling": "meeting_or_scheduling_request",
    "meeting": "meeting_or_scheduling_request",
    "legal": "contract_or_legal_related",
    "billing_dispute": "invoice_or_payment_related",
    "pricing": "pricing_request",
    "partnership": "partnership_request",
    "job": "job_or_career_inquiry",
    "career": "job_or_career_inquiry",
    "vendor": "vendor_or_supplier_offer",
    "newsletter": "newsletter_or_marketing",
    "marketing": "newsletter_or_marketing",
}

HIGH_RISK_INTENTS: FrozenSet[str] = frozenset(
    {
        "complaint_or_escalation",
        "contract_or_legal_related",
        "invoice_or_payment_related",
    }
)

AUTO_REPLY_INTENTS: FrozenSet[str] = frozenset(
    {
        "new_lead",
        "service_inquiry",
        "sales_opportunity",
        "pricing_request",
        "consultation_request",
        "partnership_request",
        "meeting_or_scheduling_request",
        "follow_up_required",
        "unknown_business_relevant",
        "vendor_or_supplier_offer",
        "job_or_career_inquiry",
    }
)

ARCHIVE_INTENTS: FrozenSet[str] = frozenset(
    {"spam_or_low_value", "newsletter_or_marketing", "not_business_relevant"}
)

CRM_UPSERT_INTENTS: FrozenSet[str] = frozenset(
    {
        "new_lead",
        "service_inquiry",
        "sales_opportunity",
        "pricing_request",
        "consultation_request",
        "partnership_request",
        "job_or_career_inquiry",
        "vendor_or_supplier_offer",
        "unknown_business_relevant",
    }
)


def normalize_intent(raw: Any, *, default: str = "unknown_business_relevant") -> str:
    """Map arbitrary model output to a canonical primary intent."""
    if raw is None:
        return default
    key = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
    if not key:
        return default
    if key in PRIMARY_INTENT_SET:
        return key
    if key in LEGACY_INTENT_MAP:
        return LEGACY_INTENT_MAP[key]
    # Partial alias match (e.g. "service_inquiry_request")
    for alias, canonical in LEGACY_INTENT_MAP.items():
        if alias in key or key in alias:
            return canonical
    for intent in PRIMARY_EMAIL_INTENTS:
        if intent in key or key in intent:
            return intent
    return default


def legacy_intent_for_compat(canonical: str) -> str:
    """Reverse map for code paths still expecting legacy intent strings."""
    reverse = {
        "new_lead": "lead_inquiry",
        "service_inquiry": "lead_inquiry",
        "sales_opportunity": "lead_inquiry",
        "pricing_request": "lead_inquiry",
        "consultation_request": "lead_inquiry",
        "existing_customer_support": "support_request",
        "complaint_or_escalation": "complaint",
        "spam_or_low_value": "spam",
        "newsletter_or_marketing": "spam",
        "not_business_relevant": "spam",
        "meeting_or_scheduling_request": "general_info",
        "unknown_business_relevant": "general_info",
    }
    return reverse.get(canonical, "general_info")


def recommended_action_type(intent: str) -> str:
    if intent in ARCHIVE_INTENTS:
        return "archive"
    if intent in AUTO_REPLY_INTENTS:
        return "auto_reply"
    if intent == "existing_customer_support":
        return "auto_reply"
    return "mark_read"


def is_high_risk_intent(intent: str) -> bool:
    return normalize_intent(intent) in HIGH_RISK_INTENTS


def should_capture_crm(intent: str) -> bool:
    return normalize_intent(intent) in CRM_UPSERT_INTENTS


def intent_labels_for_prompt(custom_labels: Optional[List[str]] = None) -> List[str]:
    labels = list(PRIMARY_EMAIL_INTENTS)
    if custom_labels:
        for label in custom_labels:
            cleaned = str(label).strip().lower().replace(" ", "_")
            if cleaned and cleaned not in labels:
                labels.append(cleaned)
    return labels
