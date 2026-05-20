"""Risk policy for AI-driven email actions."""

from typing import Any, Dict, List

from core.ai.email_intent_taxonomy import is_high_risk_intent, normalize_intent

# Legacy aliases kept for direct imports in older tests
HIGH_RISK_INTENTS = {
    "complaint",
    "escalation",
    "legal",
    "billing_dispute",
    "complaint_or_escalation",
    "contract_or_legal_related",
    "invoice_or_payment_related",
}


def evaluate_email_risk(analysis: Dict[str, Any], confidence_threshold: float = 0.7) -> Dict[str, Any]:
    """Evaluate risk signals and determine if human review is required."""
    payload = analysis if isinstance(analysis, dict) else {}
    intent = normalize_intent(payload.get("intent"))
    confidence_raw = payload.get("confidence", 0.0)
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.0

    reasons: List[str] = []
    if confidence < confidence_threshold:
        reasons.append(f"confidence_below_threshold:{confidence:.2f}")
    if is_high_risk_intent(intent) or intent in HIGH_RISK_INTENTS:
        reasons.append(f"high_risk_intent:{intent}")
    if bool(payload.get("needs_human_review")):
        reasons.append("llm_requested_human_review")

    return {
        "requires_human_review": len(reasons) > 0,
        "confidence": confidence,
        "intent": intent,
        "reasons": reasons,
    }

