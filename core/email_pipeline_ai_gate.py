"""
Optional cost controls for mailbox AI (inbound ``orchestrate_incoming``).

When ``FIKIRI_EMAIL_PIPELINE_AI_GATE`` is enabled (1/true/yes/on), the pipeline
applies the same **tier** and **budget** checks used by HTTP AI routes before
the first LLM-heavy step, and records ``ai_responses`` usage after a successful
analyze — mirroring ``routes/business.py`` ``/ai/analyze-email``. Before an
executed ``auto_reply`` when AI is enabled, the pipeline re-checks tier/budget
and records one additional ``ai_responses`` increment for the reply LLM.

Unset or false: **no behavior change** (legacy paths unchanged).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


def email_pipeline_ai_gate_enabled() -> bool:
    v = (os.getenv("FIKIRI_EMAIL_PIPELINE_AI_GATE") or "").strip().lower()
    return v in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class EmailPipelineAIGateDecision:
    allowed: bool
    reason: str


def evaluate_email_pipeline_ai_gate(user_id: Optional[int]) -> EmailPipelineAIGateDecision:
    """
    Return allowed=True when the mailbox may run AI for this user.

    When the feature flag is off, always returns allowed=True with reason
    ``flag_off`` (callers should not block or record based on that alone).
    """
    if not email_pipeline_ai_gate_enabled():
        return EmailPipelineAIGateDecision(True, "flag_off")

    if not user_id:
        logger.warning("email_pipeline_ai_gate: missing user_id; allowing AI (fail-open)")
        return EmailPipelineAIGateDecision(True, "no_user")

    try:
        from core.tier_usage_caps import check_tier_usage_cap

        ok, msg, code = check_tier_usage_cap(user_id, "ai_responses", projected_increment=1)
        if not ok:
            logger.info(
                "email_pipeline_ai_gate: tier cap blocked user_id=%s code=%s msg=%s",
                user_id,
                code,
                msg,
            )
            return EmailPipelineAIGateDecision(False, code or "PLAN_LIMIT_EXCEEDED")
    except Exception as exc:
        logger.warning("email_pipeline_ai_gate: tier check error user_id=%s: %s", user_id, exc)
        return EmailPipelineAIGateDecision(True, "tier_check_error_fail_open")

    try:
        from core.ai_budget_guardrails import ai_budget_guardrails

        budget = ai_budget_guardrails.evaluate(user_id, projected_increment=1)
        if not budget.allowed:
            logger.info(
                "email_pipeline_ai_gate: budget blocked user_id=%s reason=%s",
                user_id,
                budget.reason,
            )
            return EmailPipelineAIGateDecision(False, "AI_BUDGET_SOFT_STOP")
    except Exception as exc:
        logger.warning("email_pipeline_ai_gate: budget check error user_id=%s: %s", user_id, exc)
        return EmailPipelineAIGateDecision(True, "budget_check_error_fail_open")

    return EmailPipelineAIGateDecision(True, "")


def record_email_pipeline_ai_usage(user_id: Optional[int], quantity: int = 1) -> None:
    """Increment ``ai_responses`` for budget accounting when the gate flag is on."""
    if not email_pipeline_ai_gate_enabled() or not user_id or quantity <= 0:
        return
    try:
        from core.ai_budget_guardrails import ai_budget_guardrails

        ai_budget_guardrails.record_ai_usage(user_id, quantity)
    except Exception as exc:
        logger.warning("email_pipeline_ai_gate: record_ai_usage failed user_id=%s: %s", user_id, exc)
