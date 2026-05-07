"""Auto-send policy for AI-generated email drafts."""

from typing import Any, Dict


def can_auto_send(analysis: Dict[str, Any], risk_result: Dict[str, Any]) -> bool:
    """Allow auto-send only when model suggests it and risk policy is clear."""
    payload = analysis if isinstance(analysis, dict) else {}
    risk = risk_result if isinstance(risk_result, dict) else {}
    llm_requested_auto_send = bool(payload.get("should_auto_send"))
    requires_human_review = bool(risk.get("requires_human_review"))
    return llm_requested_auto_send and not requires_human_review

