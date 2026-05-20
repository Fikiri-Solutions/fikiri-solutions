"""
Layered email intent classification helpers (preprocess → rules → AI normalize).

Parsing stays in email_automation/parser.py; LLM calls stay in ai_assistant.py.
This module owns taxonomy normalization, rule hints, and structured output shaping.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from core.ai.email_intent_taxonomy import (
    CRM_UPSERT_INTENTS,
    HIGH_RISK_INTENTS,
    legacy_intent_for_compat,
    normalize_intent,
    recommended_action_type,
)
from core.client_email_config import load_client_email_config

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_RE = re.compile(
    r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)


def preprocess_email_metadata(
    *,
    subject: str,
    body: str,
    sender_email: str = "",
    sender_name: str = "",
) -> Dict[str, Any]:
    """Deterministic metadata extraction before AI."""
    combined = f"{subject}\n{body}".strip()
    return {
        "subject_length": len(subject or ""),
        "body_length": len(body or ""),
        "has_question_mark": "?" in combined,
        "emails_in_body": EMAIL_RE.findall(combined)[:5],
        "phones_in_body": PHONE_RE.findall(combined)[:3],
        "sender_email": (sender_email or "").strip().lower(),
        "sender_name": (sender_name or "").strip(),
    }


def build_rule_hints(
    *,
    subject: str,
    body: str,
    client_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Rule-based hints from client config + lightweight keyword patterns.
    Hints are advisory; AI + normalizer make the final call.
    """
    cfg = client_config or {}
    text = f"{subject}\n{body}".lower()
    hints: Dict[str, Any] = {
        "suggested_intents": [],
        "signals": [],
        "lead_score_boost": 0,
    }

    def add(intent: str, signal: str, boost: int = 0) -> None:
        canonical = normalize_intent(intent)
        if canonical not in hints["suggested_intents"]:
            hints["suggested_intents"].append(canonical)
        hints["signals"].append(signal)
        hints["lead_score_boost"] += boost

    for kw in cfg.get("high_value_keywords") or []:
        if kw and str(kw).lower() in text:
            add("sales_opportunity", f"high_value_keyword:{kw}", 10)

    for kw in cfg.get("low_value_keywords") or []:
        if kw and str(kw).lower() in text:
            add("spam_or_low_value", f"low_value_keyword:{kw}", -20)

    patterns = [
        (r"\b(price|pricing|quote|cost|budget|rfp)\b", "pricing_request", 12),
        (r"\b(crypto|bitcoin|guaranteed returns|act now|limited[- ]time)\b", "spam_or_low_value", -15),
        (r"\b(partner|partnership|collaborat)\b", "partnership_request", 10),
        (r"\b(job|career|hiring|resume|cv)\b", "job_or_career_inquiry", 5),
        (r"\b(invoice|payment|refund|billing)\b", "invoice_or_payment_related", 0),
        (r"\b(contract|legal|nda|agreement)\b", "contract_or_legal_related", 0),
        (r"\b(meeting|schedule|calendar|call)\b", "meeting_or_scheduling_request", 8),
        (r"\b(support|bug|issue|problem|broken|not working)\b", "existing_customer_support", 0),
        (r"\b(complaint|unhappy|disappointed|escalat)\b", "complaint_or_escalation", 0),
        (r"\b(unsubscribe|newsletter|promo|sale)\b", "newsletter_or_marketing", -5),
        (r"\b(invest|investment|funding|acquisition)\b", "sales_opportunity", 15),
    ]
    for pattern, intent, boost in patterns:
        if re.search(pattern, text):
            add(intent, f"pattern:{intent}", boost)

    if "?" in text and any(w in text for w in ("service", "help", "offer", "provide")):
        add("service_inquiry", "service_question", 8)

    return hints


def _clamp_score(value: Any, default: int = 50) -> int:
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        n = default
    return max(0, min(100, n))


def normalize_business_analysis(
    data: Dict[str, Any],
    *,
    rule_hints: Optional[Dict[str, Any]] = None,
    sender_email: str = "",
    sender_name: str = "",
    client_config: Optional[Dict[str, Any]] = None,
    schema_version: str = "2026-05-email-analysis-v2",
) -> Dict[str, Any]:
    """
    Validate/shape AI or fallback output into the v2 analysis contract.

    Preserves legacy top-level keys used by pipeline.py and policies.
    """
    if not isinstance(data, dict):
        data = {}

    cfg = client_config or {}
    hints = rule_hints or {}
    intent = normalize_intent(data.get("intent"))
    if hints.get("suggested_intents") and intent == "unknown_business_relevant":
        intent = normalize_intent(hints["suggested_intents"][0])

    secondary_raw = data.get("secondary_intents") or []
    secondary: List[str] = []
    if isinstance(secondary_raw, list):
        for item in secondary_raw:
            canon = normalize_intent(item, default="")
            if canon and canon != intent and canon not in secondary:
                secondary.append(canon)

    confidence = float(data.get("confidence_score", data.get("confidence", 0.0)) or 0.0)
    confidence = max(0.0, min(1.0, confidence))

    boost = int(hints.get("lead_score_boost") or 0)
    lead_score = _clamp_score(data.get("lead_score"), 40 if intent in CRM_UPSERT_INTENTS else 20)
    lead_score = _clamp_score(lead_score + boost, lead_score)

    urgency_score = _clamp_score(
        data.get("urgency_score"),
        {"high": 85, "medium": 55, "low": 25}.get(
            str(data.get("urgency") or "medium").lower(), 55
        ),
    )
    business_value_score = _clamp_score(
        data.get("business_value_score"),
        {"high": 80, "medium": 55, "low": 25}.get(
            str(data.get("business_value") or "medium").lower(), 55
        ),
    )

    crm_updates = data.get("crm_updates") if isinstance(data.get("crm_updates"), dict) else {}
    tags = crm_updates.get("tags") if isinstance(crm_updates.get("tags"), list) else []
    tags = [str(t) for t in tags if str(t).strip()]
    if intent not in tags:
        tags.append(intent)

    extracted = data.get("extracted_details") if isinstance(data.get("extracted_details"), dict) else {}
    recommended = data.get("recommended_action") if isinstance(data.get("recommended_action"), dict) else {}
    reply_guidance = data.get("reply_guidance") if isinstance(data.get("reply_guidance"), dict) else {}

    next_best = (
        recommended.get("next_best_action")
        or data.get("recommended_action")
        or data.get("recommended_action_type")
        or "draft_reply"
    )
    if isinstance(next_best, dict):
        next_best = "draft_reply"

    crm_action = recommended.get("crm_action")
    if not crm_action:
        crm_action = "create_or_update_lead" if intent in CRM_UPSERT_INTENTS else "none"

    workflow = recommended.get("workflow") or _default_workflow(intent)

    needs_human_review = bool(data.get("needs_human_review"))
    should_auto_send = bool(data.get("should_auto_send"))

    esc = cfg.get("escalation_rules") or {}
    if confidence < float(esc.get("min_confidence_auto_send", 0.85)):
        needs_human_review = True
        should_auto_send = False
    if intent in HIGH_RISK_INTENTS or esc.get("complaint_always_review") and intent == "complaint_or_escalation":
        needs_human_review = True
        should_auto_send = False
    if confidence < 0.7:
        needs_human_review = True
        should_auto_send = False
    if should_auto_send and needs_human_review:
        should_auto_send = False

    reason = str(data.get("reasoning_summary") or data.get("reason_for_recommendation") or "").strip()
    if hints.get("signals") and not reason:
        reason = "Rule hints: " + ", ".join(hints["signals"][:3])

    legacy_intent = legacy_intent_for_compat(intent)
    urgency_label = str(data.get("urgency") or _score_to_label(urgency_score)).lower()
    business_value_label = str(data.get("business_value") or _score_to_label(business_value_score)).lower()

    out: Dict[str, Any] = {
        "schema_version": schema_version,
        "intent": intent,
        "legacy_intent": legacy_intent,
        "secondary_intents": secondary,
        "confidence_score": confidence,
        "confidence": confidence,
        "lead_score": lead_score,
        "urgency_score": urgency_score,
        "business_value_score": business_value_score,
        "urgency": urgency_label,
        "business_value": business_value_label,
        "summary": str(data.get("summary") or "").strip(),
        "recommended_action": str(next_best),
        "recommended_action_type": recommended_action_type(intent),
        "tone": str(data.get("tone") or reply_guidance.get("tone") or cfg.get("preferred_tone") or "professional_warm"),
        "crm_updates": {
            "stage": str(crm_updates.get("stage") or _default_stage(intent)),
            "tags": tags,
            "follow_up_needed": bool(crm_updates.get("follow_up_needed", intent in CRM_UPSERT_INTENTS)),
            "priority": str(crm_updates.get("priority") or urgency_label),
        },
        "sender": {
            "name": str(data.get("sender_name") or sender_name or "").strip(),
            "email": str(data.get("sender_email") or sender_email or "").strip(),
            "company": str(extracted.get("company_name") or data.get("company_name") or "").strip(),
            "phone": str(extracted.get("phone") or data.get("phone") or "").strip(),
        },
        "extracted_details": {
            "requested_service": str(extracted.get("requested_service") or "").strip(),
            "budget_signal": str(extracted.get("budget_signal") or extracted.get("budget_or_price_signal") or "").strip(),
            "timeline_signal": str(extracted.get("timeline_signal") or "").strip(),
            "pain_points": extracted.get("pain_points") if isinstance(extracted.get("pain_points"), list) else [],
        },
        "recommended_action_detail": {
            "next_best_action": str(next_best),
            "crm_action": crm_action,
            "workflow": workflow,
        },
        "reply_guidance": {
            "tone": str(reply_guidance.get("tone") or data.get("tone") or cfg.get("preferred_tone") or "professional_warm"),
            "should_auto_draft": bool(reply_guidance.get("should_auto_draft", True)),
            "should_auto_send": should_auto_send,
        },
        "suggested_reply": str(data.get("suggested_reply") or "").strip(),
        "should_auto_send": should_auto_send,
        "needs_human_review": needs_human_review,
        "reasoning_summary": reason,
        "reason_for_recommendation": reason,
        "classification_signals": list(hints.get("signals") or []),
    }
    return out


def classify_with_fallback(
    *,
    subject: str,
    body: str,
    sender_email: str = "",
    sender_name: str = "",
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Full offline path: preprocess → rules → normalize (no LLM)."""
    cfg = load_client_email_config(user_id)
    meta = preprocess_email_metadata(
        subject=subject, body=body, sender_email=sender_email, sender_name=sender_name
    )
    hints = build_rule_hints(subject=subject, body=body, client_config=cfg)
    intent = hints["suggested_intents"][0] if hints.get("suggested_intents") else "unknown_business_relevant"
    raw = {
        "intent": intent,
        "confidence_score": 0.55 if hints.get("signals") else 0.45,
        "urgency": "medium",
        "business_value": "medium" if intent in CRM_UPSERT_INTENTS else "low",
        "summary": (body or subject or "")[:200],
        "needs_human_review": True,
        "should_auto_send": False,
        "reasoning_summary": "Heuristic classification (AI unavailable).",
    }
    return normalize_business_analysis(
        raw,
        rule_hints=hints,
        sender_email=sender_email or meta.get("sender_email", ""),
        sender_name=sender_name or meta.get("sender_name", ""),
        client_config=cfg,
    )


def _score_to_label(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _default_stage(intent: str) -> str:
    if intent in {"new_lead", "sales_opportunity", "pricing_request"}:
        return "qualified"
    if intent == "existing_customer_support":
        return "replied"
    return "contacted"


def _default_workflow(intent: str) -> str:
    mapping = {
        "new_lead": "new_lead_followup",
        "service_inquiry": "service_inquiry_followup",
        "pricing_request": "pricing_followup",
        "partnership_request": "partnership_review",
        "job_or_career_inquiry": "hr_routing",
        "complaint_or_escalation": "escalation_queue",
        "meeting_or_scheduling_request": "scheduling_assist",
        "existing_customer_support": "support_ticket",
    }
    return mapping.get(intent, "manual_review")
