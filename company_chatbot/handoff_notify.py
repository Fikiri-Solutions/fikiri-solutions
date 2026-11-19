"""
Fail-open Slack alerts for *explicit* site-bot human handoffs.

Ordinary grounded answers and soft CTAs must not notify. Only:
  - guard-driven handoffs (frustration / stuck / turn cap / repeat)
  - explicit contact mode
  - completed intake with a captured email
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from company_chatbot import config
from company_chatbot.schemas import MessageResult

logger = logging.getLogger(__name__)

_GUARD_SIGNAL = "guard_handoff"


def is_explicit_human_handoff(result: MessageResult) -> bool:
    if not result.handoff.applicable:
        return False

    signals = list(result.lead_intent.signals or [])
    if _GUARD_SIGNAL in signals:
        return True

    if result.mode == config.MODE_CONTACT:
        return True

    intake = result.intake or {}
    if intake.get("complete") and result.lead_intent.capture_ready:
        return True

    return False


def handoff_notify_reason(result: MessageResult) -> str:
    signals = list(result.lead_intent.signals or [])
    if _GUARD_SIGNAL in signals:
        # second signal is typically the guard reason
        for s in signals:
            if s and s != _GUARD_SIGNAL:
                return f"guard:{s}"
        return "guard"
    if result.mode == config.MODE_CONTACT:
        return "contact"
    if (result.intake or {}).get("complete"):
        return "intake_complete"
    return "handoff"


def notify_site_chat_handoff(
    *,
    session_id: str,
    result: MessageResult,
    user_message: str = "",
) -> bool:
    """
    Enqueue a Slack lead alert for an explicit handoff. Fail-open; never raises.
    Returns True if accepted for delivery (configured + not deduped).
    """
    if not is_explicit_human_handoff(result):
        return False

    try:
        from core.lead_form_notifications import lead_dedupe_key, send_lead_slack_notification
    except Exception as e:
        logger.warning("Site chat handoff Slack unavailable: %s", e)
        return False

    reason = handoff_notify_reason(result)
    assessment = result.lead_assessment
    synopsis = (assessment.synopsis or "").strip()
    preview = (user_message or "").strip()
    if len(preview) > 280:
        preview = preview[:277] + "..."

    intake = result.intake or {}
    slots = intake.get("slots") if isinstance(intake.get("slots"), dict) else {}
    email = str(slots.get("contact_email") or slots.get("email") or "").strip()
    industry = str(slots.get("industry") or "").strip()

    fields = [
        {"title": "Session", "value": session_id[:64], "short": True},
        {"title": "Reason", "value": reason, "short": True},
        {"title": "Tier", "value": assessment.tier or "—", "short": True},
        {"title": "Score", "value": str(assessment.score), "short": True},
        {
            "title": "Path",
            "value": result.handoff.secondary or result.handoff.handoff_type or "—",
            "short": True,
        },
    ]
    if email:
        fields.append({"title": "Email", "value": email, "short": True})
    if industry:
        fields.append({"title": "Industry", "value": industry, "short": True})
    if synopsis:
        fields.append({"title": "Synopsis", "value": synopsis[:400], "short": False})
    if preview:
        fields.append({"title": "Last message", "value": preview, "short": False})

    return send_lead_slack_notification(
        title=f"Site chat handoff: {reason}",
        text=synopsis or preview or "Visitor needs a human follow-up.",
        fields=fields,
        dedupe_key=lead_dedupe_key("site_chat", session_id, reason),
        blocking=False,
    )
