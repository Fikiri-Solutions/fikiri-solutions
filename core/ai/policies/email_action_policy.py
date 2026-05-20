"""Policy orchestration for inbound AI email actions."""

from typing import Any, Dict

from core.ai.email_intent_taxonomy import normalize_intent, recommended_action_type
from core.ai.policies.auto_send_policy import can_auto_send
from core.ai.policies.risk_policy import evaluate_email_risk


def evaluate_email_action_policy(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Return deterministic execution policy from structured AI analysis."""
    payload = analysis if isinstance(analysis, dict) else {}
    intent = normalize_intent(payload.get("intent"))
    risk = evaluate_email_risk(payload)
    should_auto_send = can_auto_send(payload, risk)
    action_type = payload.get("recommended_action_type") or recommended_action_type(intent)
    execution_mode = "execute" if should_auto_send else "draft_only"
    reason = str(payload.get("reason_for_recommendation") or "").strip()
    if not reason:
        reason = "Policy default: draft for human review."
    if risk.get("reasons"):
        reason = "; ".join([reason] + list(risk["reasons"]))

    return {
        "intent": intent,
        "recommended_action_type": action_type,
        "requires_human_review": bool(risk.get("requires_human_review")),
        "should_auto_send": should_auto_send,
        "should_execute_action": execution_mode == "execute",
        "execution_mode": execution_mode,
        "reason": reason,
        "risk": risk,
    }

