"""
Chatbot usage tracking and billing helpers for the public widget path.

Encapsulates plan/tier/budget gates and billing/API usage recording. Route auth stays
in public_chatbot_api.py.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.ai_budget_guardrails import ai_budget_guardrails
from core.api_key_manager import api_key_manager
from core.database_optimization import db_optimizer
from core.tier_usage_caps import check_tier_usage_cap

logger = logging.getLogger(__name__)


@dataclass
class ChatbotUsageGateResult:
    allowed: bool
    http_status: int = 200
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    error_extra: Dict[str, Any] = field(default_factory=dict)
    plan_info: Dict[str, Any] = field(default_factory=lambda: {"plan": "unknown", "allow_llm": True})
    allow_llm: bool = True


def _blocked_reason_for_gate(
    *,
    allow_llm: bool,
    error_code: Optional[str],
) -> str:
    if not allow_llm:
        return "plan_not_allowed"
    if error_code == "AI_BUDGET_SOFT_STOP":
        return "ai_budget_soft_stop"
    if error_code == "PLAN_LIMIT_EXCEEDED":
        return "tier_cap_exceeded"
    return error_code or "usage_blocked"


def _log_usage_event(message: str, *, level: str = "info", **fields: Any) -> None:
    extra: Dict[str, Any] = {
        "service": "chatbot",
        "severity": "INFO" if level == "info" else "WARN",
    }
    for key, value in fields.items():
        if value is not None:
            extra[key] = value
    log_fn = logger.info if level == "info" else logger.warning
    log_fn(message, extra=extra)


def _log_usage_blocked(
    *,
    user_id: Optional[Any],
    tenant_id: Optional[str],
    billing_uid: Optional[int],
    blocked_reason: str,
    error_code: Optional[str],
    fallback_needed: bool,
) -> None:
    _log_usage_event(
        "chatbot usage blocked",
        event="chatbot.usage.blocked",
        user_id=user_id,
        tenant_id=tenant_id,
        billing_uid=billing_uid,
        blocked_reason=blocked_reason,
        error_code=error_code,
        fallback_needed=fallback_needed,
    )


def check_plan_access(user_id: Optional[Any]) -> Dict[str, Any]:
    if os.getenv("FLASK_ENV") == "test" or os.getenv("PYTEST_CURRENT_TEST"):
        return {"plan": "test", "allow_llm": True}
    if not user_id or not db_optimizer.table_exists("subscriptions"):
        return {"plan": "unknown", "allow_llm": True}
    try:
        sub = db_optimizer.execute_query(
            "SELECT status, tier FROM subscriptions WHERE user_id = ? ORDER BY current_period_end DESC LIMIT 1",
            (user_id,),
        )
        if sub:
            status = (sub[0].get("status") or "").lower()
            tier = (sub[0].get("tier") or "starter").lower()
            is_paid = status in {"active", "trialing"}
            return {"plan": tier if is_paid else "free", "allow_llm": is_paid}
        return {"plan": "free", "allow_llm": False}
    except Exception as exc:
        logger.warning("Plan check failed: %s", exc)
        return {"plan": "unknown", "allow_llm": True}


def check_chatbot_usage_allowed(
    *,
    user_id: Optional[Any],
    billing_uid: Optional[int],
    fallback_needed: bool,
    tenant_id: Optional[str] = None,
) -> ChatbotUsageGateResult:
    """
    Evaluate plan, tier cap, and AI budget gates before LLM generation.

    Preserves public widget semantics: unpaid plan blocks with 402; tier and budget
    checks run only when LLM would be attempted (not fallback-only).
    """
    plan_info = check_plan_access(user_id)
    allow_llm = bool(plan_info.get("allow_llm", True))
    if not allow_llm:
        blocked_reason = _blocked_reason_for_gate(allow_llm=False, error_code="PLAN_LIMIT_EXCEEDED")
        _log_usage_blocked(
            user_id=user_id,
            tenant_id=tenant_id,
            billing_uid=billing_uid,
            blocked_reason=blocked_reason,
            error_code="PLAN_LIMIT_EXCEEDED",
            fallback_needed=fallback_needed,
        )
        return ChatbotUsageGateResult(
            allowed=False,
            http_status=402,
            error_message="Plan limit exceeded",
            error_code="PLAN_LIMIT_EXCEEDED",
            plan_info=plan_info,
            allow_llm=False,
        )

    if allow_llm and not fallback_needed and billing_uid is not None:
        tier_ok, tier_msg, tier_code = check_tier_usage_cap(
            billing_uid, "ai_responses", projected_increment=1
        )
        if not tier_ok:
            blocked_reason = _blocked_reason_for_gate(allow_llm=True, error_code=tier_code)
            _log_usage_blocked(
                user_id=user_id,
                tenant_id=tenant_id,
                billing_uid=billing_uid,
                blocked_reason=blocked_reason,
                error_code=tier_code or "PLAN_LIMIT_EXCEEDED",
                fallback_needed=fallback_needed,
            )
            return ChatbotUsageGateResult(
                allowed=False,
                http_status=402,
                error_message=tier_msg or "Plan limit exceeded",
                error_code=tier_code or "PLAN_LIMIT_EXCEEDED",
                plan_info=plan_info,
                allow_llm=allow_llm,
            )

        budget_decision = ai_budget_guardrails.evaluate(billing_uid, projected_increment=1)
        if not budget_decision.allowed:
            blocked_reason = _blocked_reason_for_gate(allow_llm=True, error_code="AI_BUDGET_SOFT_STOP")
            _log_usage_blocked(
                user_id=user_id,
                tenant_id=tenant_id,
                billing_uid=billing_uid,
                blocked_reason=blocked_reason,
                error_code="AI_BUDGET_SOFT_STOP",
                fallback_needed=fallback_needed,
            )
            return ChatbotUsageGateResult(
                allowed=False,
                http_status=402,
                error_message=(
                    "AI monthly budget cap reached. Upgrade or wait until next billing period."
                    if budget_decision.reason == "monthly_budget_cap_reached"
                    else "AI monthly budget approval required."
                ),
                error_code="AI_BUDGET_SOFT_STOP",
                error_extra={
                    "tier": budget_decision.tier,
                    "month": budget_decision.month,
                    "budget_cap_usd": budget_decision.budget_cap_usd,
                    "estimated_cost_usd": budget_decision.estimated_cost_usd,
                    "projected_cost_usd": budget_decision.projected_cost_usd,
                    "requires_approval": budget_decision.requires_approval,
                },
                plan_info=plan_info,
                allow_llm=allow_llm,
            )

    return ChatbotUsageGateResult(
        allowed=True,
        plan_info=plan_info,
        allow_llm=allow_llm,
    )


def record_chatbot_request_usage(
    *,
    api_key_id: Optional[int],
    endpoint: Optional[str],
    ip_address: Optional[str],
    user_agent: Optional[str],
    response_status: Optional[int] = None,
    response_time_ms: Optional[int] = None,
    user_id: Optional[Any] = None,
    tenant_id: Optional[str] = None,
) -> None:
    """Record per-request API key usage for the public chatbot widget."""
    if api_key_id is None:
        return
    try:
        api_key_manager.record_usage(
            api_key_id=api_key_id,
            endpoint=endpoint,
            ip_address=ip_address,
            user_agent=user_agent,
            response_status=response_status,
            response_time_ms=response_time_ms,
        )
        _log_usage_event(
            "chatbot request usage recorded",
            event="chatbot.usage.request_recorded",
            api_key_id=api_key_id,
            user_id=user_id,
            tenant_id=tenant_id,
            response_status=response_status,
            response_time_ms=response_time_ms,
        )
    except Exception as exc:
        logger.error("Failed to record API usage: %s", exc)


def record_chatbot_billing_usage(
    user_id: Optional[int],
    usage_type: str,
    quantity: int = 1,
    *,
    tenant_id: Optional[str] = None,
) -> bool:
    if not user_id:
        return False
    if os.getenv("FLASK_ENV") == "test" or os.getenv("PYTEST_CURRENT_TEST"):
        return False
    if not db_optimizer.table_exists("billing_usage"):
        return False
    try:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        db_optimizer.execute_query(
            "INSERT INTO billing_usage (user_id, month, usage_type, quantity) VALUES (?, ?, ?, ?)",
            (user_id, month, usage_type, quantity),
            fetch=False,
        )
        _log_usage_event(
            "chatbot billing usage recorded",
            event="chatbot.usage.billing_recorded",
            user_id=user_id,
            tenant_id=tenant_id,
            usage_type=usage_type,
            billing_recorded=True,
        )
        return True
    except Exception as exc:
        logger.warning("Failed to record billing usage: %s", exc)
        return False


def should_record_chatbot_ai_usage(
    *,
    billing_uid: Optional[int],
    llm_attempted: bool,
    llm_result_meta: Dict[str, Any],
) -> bool:
    return bool(
        llm_attempted
        and llm_result_meta.get("llm_success")
        and llm_result_meta.get("llm_validated")
        and billing_uid is not None
    )


def record_chatbot_ai_usage_if_needed(
    *,
    billing_uid: Optional[int],
    llm_attempted: bool,
    llm_result_meta: Dict[str, Any],
    tenant_id: Optional[str] = None,
) -> bool:
    """
    Record AI budget usage when LLM was attempted, succeeded, and validated.

    Returns whether usage was recorded.
    """
    llm_success = bool(llm_result_meta.get("llm_success"))
    llm_validated = bool(llm_result_meta.get("llm_validated"))
    if not should_record_chatbot_ai_usage(
        billing_uid=billing_uid,
        llm_attempted=llm_attempted,
        llm_result_meta=llm_result_meta,
    ):
        return False
    ai_budget_guardrails.record_ai_usage(billing_uid, 1)
    try:
        from analytics.service_usage_analytics import record_chatbot_service_usage
        from analytics.service_usage_constants import METRIC_AI_RESPONSES

        record_chatbot_service_usage(
            billing_uid,
            metric_name=METRIC_AI_RESPONSES,
            correlation_id=tenant_id,
            llm_success=True,
        )
    except Exception as exc:
        logger.debug("chatbot service usage analytics skipped: %s", exc)
    _log_usage_event(
        "chatbot ai usage recorded",
        event="chatbot.usage.ai_recorded",
        user_id=billing_uid,
        tenant_id=tenant_id,
        llm_attempted=llm_attempted,
        llm_success=llm_success,
        llm_validated=llm_validated,
        ai_usage_recorded=True,
    )
    return True
