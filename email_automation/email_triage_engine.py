"""
Email Triage Engine: rules first, optional AI enrichment via existing intent analysis.

Never auto-deletes mail; cleanup_action is a recommendation for user-approved bulk ops.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from core.ai.email_triage_taxonomy import (
    category_from_intent,
    default_cleanup_for_category,
    normalize_cleanup_action,
    normalize_triage_category,
    suggested_gmail_labels,
)
from core.client_email_config import load_client_email_config
from email_automation.email_intent_classifier import (
    build_rule_hints,
    classify_with_fallback,
    preprocess_email_metadata,
)
from email_automation.email_triage_operational_rules import (
    cap_lead_if_automated,
    match_operational_notification,
)

logger = logging.getLogger(__name__)

RULE_CONFIDENCE_HIGH = 0.82
RULE_CONFIDENCE_LOW = 0.55

_LIST_UNSUB_RE = re.compile(r"list-unsubscribe|unsubscribe", re.I)
_NOREPLY_RE = re.compile(r"noreply|no-reply|donotreply|do-not-reply|mailer-daemon", re.I)
_MARKETING_RE = re.compile(
    r"\b(promotion|promo|discount|sale|%\s*off|clearance|deal of the day)\b", re.I
)
_LEAD_RE = re.compile(
    r"\b(quote|estimate|consultation|interested in|pricing|rfp|proposal|demo)\b", re.I
)
_SYSTEM_RE = re.compile(
    r"\b(password reset|security alert|verification code|sign-in|login attempt)\b", re.I
)
_SPAM_RISK_RE = re.compile(
    r"\b(lottery|wire transfer|gift card|act now|guaranteed returns|bitcoin opportunity)\b",
    re.I,
)
_EXISTING_CLIENT_RE = re.compile(
    r"\b(re:|fwd:|follow[- ]?up|your order|account update|subscription renew)\b", re.I
)


@dataclass
class TriageResult:
    category: str
    lead_score: int
    business_relevance_score: int
    urgency_score: int
    cleanup_action: str
    confidence: float
    reason: str
    suggested_labels: List[str] = field(default_factory=list)
    classification_source: str = "rules"
    intent_canonical: Optional[str] = None
    needs_ai: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clamp_score(value: Any, default: int = 50) -> int:
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        n = default
    return max(0, min(100, n))


def _rule_only_triage(
    *,
    subject: str,
    body: str,
    sender_email: str,
    sender_name: str,
    headers: Optional[Dict[str, Any]] = None,
    client_config: Optional[Dict[str, Any]] = None,
) -> TriageResult:
    text = f"{subject}\n{body}".strip()
    lower = text.lower()
    hdrs = headers or {}
    signals: List[str] = []

    # --- High-confidence rule-only paths ---
    if _LIST_UNSUB_RE.search(lower) or hdrs.get("list_unsubscribe"):
        signals.append("list_unsubscribe")
        return TriageResult(
            category="newsletter_marketing",
            lead_score=5,
            business_relevance_score=10,
            urgency_score=5,
            cleanup_action="archive",
            confidence=0.92,
            reason="Newsletter/marketing signals (unsubscribe header or keyword).",
            suggested_labels=suggested_gmail_labels("newsletter_marketing", "archive"),
            classification_source="rules",
        )

    if _NOREPLY_RE.search(sender_email) and _MARKETING_RE.search(lower):
        signals.append("noreply_marketing")
        return TriageResult(
            category="newsletter_marketing",
            lead_score=8,
            business_relevance_score=12,
            urgency_score=8,
            cleanup_action="archive",
            confidence=0.88,
            reason="Automated marketing sender (noreply + promo language).",
            suggested_labels=suggested_gmail_labels("newsletter_marketing", "archive"),
            classification_source="rules",
        )

    if _SPAM_RISK_RE.search(lower):
        signals.append("spam_risk_pattern")
        return TriageResult(
            category="spam_risk",
            lead_score=0,
            business_relevance_score=0,
            urgency_score=90,
            cleanup_action="spam_candidate",
            confidence=0.9,
            reason="High-risk spam/scam language detected.",
            suggested_labels=suggested_gmail_labels("spam_risk", "spam_candidate"),
            classification_source="rules",
        )

    if _SYSTEM_RE.search(lower):
        signals.append("system_notification")
        return TriageResult(
            category="personal_non_business",
            lead_score=0,
            business_relevance_score=5,
            urgency_score=40,
            cleanup_action="archive",
            confidence=0.86,
            reason="System/security notification (non-sales).",
            suggested_labels=suggested_gmail_labels("personal_non_business", "archive"),
            classification_source="rules",
        )

    if _MARKETING_RE.search(lower) and not _LEAD_RE.search(lower):
        signals.append("marketing_keywords")
        return TriageResult(
            category="newsletter_marketing",
            lead_score=10,
            business_relevance_score=15,
            urgency_score=10,
            cleanup_action="archive",
            confidence=0.8,
            reason="Promotional/marketing language without a business inquiry.",
            suggested_labels=suggested_gmail_labels("newsletter_marketing", "archive"),
            classification_source="rules",
        )

    op_match = match_operational_notification(
        subject=subject,
        body=body,
        sender_email=sender_email,
        sender_name=sender_name,
    )
    if op_match:
        signals.append(op_match.get("signal", "operational_notification"))
        cat = normalize_triage_category(op_match["category"])
        lead_score = _clamp_score(op_match["lead_score"])
        return TriageResult(
            category=cat,
            lead_score=lead_score,
            business_relevance_score=_clamp_score(op_match["business_relevance_score"]),
            urgency_score=_clamp_score(op_match["urgency_score"]),
            cleanup_action=normalize_cleanup_action(
                default_cleanup_for_category(cat, lead_score=lead_score)
            ),
            confidence=float(op_match["confidence"]),
            reason=str(op_match["reason"]),
            suggested_labels=suggested_gmail_labels(
                cat, default_cleanup_for_category(cat, lead_score=lead_score)
            ),
            classification_source="rules",
            needs_ai=False,
        )

    # --- Intent hints (existing rule pack) ---
    hints = build_rule_hints(subject=subject, body=body, client_config=client_config or {})
    intent = hints["suggested_intents"][0] if hints.get("suggested_intents") else ""
    boost = int(hints.get("lead_score_boost") or 0)

    if _LEAD_RE.search(lower):
        signals.append("lead_keywords")
        category = "business_lead"
        lead_score = _clamp_score(55 + boost, 55)
        biz = _clamp_score(70 + boost, 70)
        urgency = 50
        confidence = 0.78 if intent else 0.72
        reason = "Possible lead (quote/pricing/consultation language)."
    elif intent:
        category = category_from_intent(intent)
        lead_score = _clamp_score(40 + boost, 40)
        biz = _clamp_score(50 + boost, 50)
        urgency = 45 if category == "action_needed" else 30
        confidence = 0.75 if len(hints.get("signals") or []) >= 2 else 0.65
        reason = f"Rule hints suggest intent `{intent}`."
        signals.extend(hints.get("signals") or [])
    elif _EXISTING_CLIENT_RE.search(lower):
        category = "existing_client"
        lead_score = 25
        biz = 55
        urgency = 40
        confidence = 0.7
        reason = "Thread/order language suggests existing client communication."
    else:
        category = "review_needed"
        lead_score = 20
        biz = 30
        urgency = 25
        confidence = 0.45
        reason = "No strong rule match; needs review or AI enrichment."

    category = cap_lead_if_automated(
        category=category,
        subject=subject,
        body=body,
        sender_email=sender_email,
    )
    if category != "business_lead" and category in (
        "action_needed",
        "newsletter_marketing",
        "review_needed",
    ):
        lead_score = min(lead_score, 25 if category == "newsletter_marketing" else 20)
        if category == "action_needed":
            urgency = max(urgency, 45)
        confidence = max(confidence, 0.8)
        reason = (
            reason
            + " (automated sender capped — not classified as lead.)"
        )[:500]

    cleanup = default_cleanup_for_category(category, lead_score=lead_score)
    needs_ai = confidence < RULE_CONFIDENCE_LOW or (
        confidence < RULE_CONFIDENCE_HIGH
        and category in ("review_needed", "business_lead", "action_needed", "vendor_partner")
    )

    return TriageResult(
        category=normalize_triage_category(category),
        lead_score=lead_score,
        business_relevance_score=biz,
        urgency_score=urgency,
        cleanup_action=normalize_cleanup_action(cleanup),
        confidence=round(confidence, 3),
        reason=reason,
        suggested_labels=suggested_gmail_labels(category, cleanup),
        classification_source="rules",
        intent_canonical=intent or None,
        needs_ai=needs_ai,
    )


def _enrich_from_analysis(analysis: Dict[str, Any], base: TriageResult) -> TriageResult:
    intent = analysis.get("intent") or analysis.get("legacy_intent") or ""
    category = category_from_intent(str(intent))
    lead_score = _clamp_score(analysis.get("lead_score"), base.lead_score)
    biz = _clamp_score(analysis.get("business_value_score") or analysis.get("business_relevance_score"), base.business_relevance_score)
    urgency = _clamp_score(analysis.get("urgency_score"), base.urgency_score)
    conf = float(analysis.get("confidence_score") or analysis.get("confidence") or base.confidence)
    cleanup = normalize_cleanup_action(
        analysis.get("recommended_action_detail", {}).get("cleanup")
        if isinstance(analysis.get("recommended_action_detail"), dict)
        else None,
        default=default_cleanup_for_category(category, lead_score=lead_score),
    )
    reason = str(analysis.get("reasoning_summary") or analysis.get("reason_for_recommendation") or base.reason)
    return TriageResult(
        category=category,
        lead_score=lead_score,
        business_relevance_score=biz,
        urgency_score=urgency,
        cleanup_action=cleanup,
        confidence=min(0.98, max(conf, base.confidence)),
        reason=reason[:500],
        suggested_labels=suggested_gmail_labels(category, cleanup),
        classification_source=str(analysis.get("classification_source") or "ai"),
        intent_canonical=str(intent) if intent else base.intent_canonical,
        needs_ai=False,
    )


def classify_email_triage(
    *,
    subject: str,
    body: str,
    sender_email: str = "",
    sender_name: str = "",
    headers: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
    analysis: Optional[Dict[str, Any]] = None,
    allow_ai: bool = False,
) -> Dict[str, Any]:
    """
    Classify one message. Rules always run; uses ``analysis`` when provided (mailbox AI path).
    Optional ``allow_ai`` triggers classify_with_fallback only (no extra LLM) when rules are uncertain.
    """
    cfg = load_client_email_config(user_id)
    preprocess_email_metadata(
        subject=subject, body=body, sender_email=sender_email, sender_name=sender_name
    )
    base = _rule_only_triage(
        subject=subject,
        body=body,
        sender_email=sender_email,
        sender_name=sender_name,
        headers=headers,
        client_config=cfg,
    )

    if analysis and isinstance(analysis, dict):
        result = _enrich_from_analysis(analysis, base)
        return result.to_dict()

    if allow_ai and base.needs_ai:
        try:
            offline = classify_with_fallback(
                subject=subject,
                body=body,
                sender_email=sender_email,
                sender_name=sender_name,
                user_id=user_id,
            )
            result = _enrich_from_analysis(offline, base)
            result.classification_source = "rules+fallback"
            capped = cap_lead_if_automated(
                category=result.category,
                subject=subject,
                body=body,
                sender_email=sender_email,
            )
            if capped != result.category:
                result.category = normalize_triage_category(capped)
                result.lead_score = min(result.lead_score, 25)
                result.needs_ai = False
            return result.to_dict()
        except Exception as exc:
            logger.warning("triage fallback analysis failed: %s", exc)

    capped = cap_lead_if_automated(
        category=base.category,
        subject=subject,
        body=body,
        sender_email=sender_email,
    )
    if capped != base.category:
        out = base.to_dict()
        out["category"] = normalize_triage_category(capped)
        out["lead_score"] = min(int(out.get("lead_score") or 0), 25)
        out["cleanup_action"] = default_cleanup_for_category(
            out["category"], lead_score=out["lead_score"]
        )
        out["needs_ai"] = False
        return out
    return base.to_dict()
