"""Policy orchestration for inbound AI email actions."""

from typing import Any, Dict

from core.ai.policies.auto_send_policy import can_auto_send
from core.ai.policies.risk_policy import evaluate_email_risk


def _recommended_action_type(intent: str) -> str:
    if intent == "spam":
        return "archive"
    return "auto_reply"


def evaluate_email_action_policy(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Return deterministic execution policy from structured AI analysis."""
    payload = analysis if isinstance(analysis, dict) else {}
    intent = str(payload.get("intent") or "").lower()
    risk = evaluate_email_risk(payload)
    should_auto_send = can_auto_send(payload, risk)
    action_type = _recommended_action_type(intent)
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

