#!/usr/bin/env python3
"""
Email automation pipeline façade.

Orchestrates the email flow; implementation lives in:
  - email_automation/actions.py   (MinimalEmailActions, send/process)
  - email_automation/parser.py    (MinimalEmailParser)
  - email_automation/service_manager.py (EmailServiceManager, providers)
  - email_automation/jobs.py      (EmailJobManager, queue processing)

Import from here for a single pipeline entry point, or import from the
submodules directly when you need a specific component.
"""

import logging
import uuid
from typing import Any, Dict, Optional

from email_automation.parser import MinimalEmailParser
from email_automation.actions import MinimalEmailActions
from email_automation.service_manager import EmailServiceManager
from email_automation.jobs import EmailJobManager, EmailJob
from email_automation.ai_assistant import MinimalAIEmailAssistant
from email_automation.email_event_log import record_email_event
from core.automation_safety import automation_safety_manager
from core.database_optimization import db_optimizer
from crm.service import enhanced_crm_service

__all__ = [
    "MinimalEmailParser",
    "MinimalEmailActions",
    "EmailServiceManager",
    "EmailJobManager",
    "EmailJob",
    "parse_message",
    "process_incoming",
    "orchestrate_incoming",
]

logger = logging.getLogger(__name__)

# Import trace context
try:
    from core.trace_context import get_trace_id, set_trace_id
    TRACE_CONTEXT_AVAILABLE = True
except ImportError:
    TRACE_CONTEXT_AVAILABLE = False


def parse_message(message: dict) -> dict:
    """Parse a raw message via the canonical parser."""
    if not isinstance(message, dict):
        logger.warning(
            "parse_message: expected dict, got %s", type(message).__name__
        )
        return MinimalEmailParser()._create_empty_parsed_message()
    parser = MinimalEmailParser()
    return parser.parse_message(message)


def process_incoming(
    message: dict,
    actions: MinimalEmailActions = None,
    user_id: int = None,
    correlation_id: Optional[str] = None,
) -> dict:
    """
    Parse and optionally run actions on an incoming message.
    Caller can pass a configured MinimalEmailActions instance or None to only parse.
    """
    parsed = parse_message(message)
    if actions is None or user_id is None:
        return parsed
    return orchestrate_incoming(
        parsed, user_id=user_id, actions=actions, correlation_id=correlation_id
    )


def _determine_action(classification: dict) -> str:
    if not isinstance(classification, dict):
        return "mark_read"
    intent = (classification.get("intent") or "").lower()
    if intent == "spam":
        return "archive"
    if intent in ["lead_inquiry", "support_request", "general_info", "complaint"]:
        return "auto_reply"
    return "mark_read"


def _extract_sender_email(from_header: str) -> str:
    if not from_header:
        return ""
    if "<" in from_header and ">" in from_header:
        return from_header.split("<")[1].split(">")[0].strip()
    return from_header.strip()


def _action_result_details(action_result: Any) -> Dict[str, Any]:
    """Normalize process_email `details` to a dict (handlers should return dicts)."""
    if not isinstance(action_result, dict):
        return {}
    raw = action_result.get("details")
    return raw if isinstance(raw, dict) else {}


def _resolve_lead_id(user_id: int, sender_email: str) -> Optional[int]:
    if not sender_email:
        return None
    try:
        rows = db_optimizer.execute_query(
            "SELECT id FROM leads WHERE user_id = ? AND lower(email) = lower(?)",
            (user_id, sender_email),
        )
        if rows:
            return int(rows[0]["id"])
    except Exception:
        pass
    return None


def orchestrate_incoming(
    parsed: dict,
    user_id: int,
    actions: MinimalEmailActions = None,
    trace_id: str = None,
    correlation_id: Optional[str] = None,
) -> dict:
    """
    Full mailbox automation:
    parse -> classify -> decide action -> draft response -> execute action -> log to CRM
    """
    if TRACE_CONTEXT_AVAILABLE:
        if trace_id:
            set_trace_id(trace_id)
        else:
            trace_id = get_trace_id()

    if not isinstance(parsed, dict):
        logger.warning(
            "orchestrate_incoming: expected dict parsed message, got %s",
            type(parsed).__name__,
        )
        cid = correlation_id or trace_id or str(uuid.uuid4())
        return {
            "success": False,
            "error": "invalid_parsed_message",
            "correlation_id": cid,
        }

    corr = correlation_id or trace_id or str(uuid.uuid4())
    parsed["_correlation_id"] = corr

    actions = actions or MinimalEmailActions(services={"ai_assistant": MinimalAIEmailAssistant()})

    parser = MinimalEmailParser()
    subject = parser.get_subject(parsed)
    body_text = parser.get_body_text(parsed) or parsed.get("snippet", "")
    from_header = parser.get_sender(parsed)
    sender_email = _extract_sender_email(from_header)
    lead_id = _resolve_lead_id(user_id, sender_email)
    msg_id = parsed.get("message_id") or ""
    thread_id = parsed.get("thread_id")

    record_email_event(
        user_id,
        "email.parsed",
        provider="gmail",
        message_id=msg_id or None,
        thread_id=thread_id,
        lead_id=lead_id,
        correlation_id=corr,
        payload={"subject": (subject or "")[:500]},
        status="applied",
        source="email_automation.pipeline",
    )

    ai_assistant = actions.services.get("ai_assistant") or MinimalAIEmailAssistant()
    try:
        classification = ai_assistant.classify_email_intent(body_text, subject)
    except Exception as exc:
        logger.warning("Email classification failed: %s", exc)
        record_email_event(
            user_id,
            "email.failed",
            provider="gmail",
            message_id=msg_id or None,
            thread_id=thread_id,
            lead_id=lead_id,
            correlation_id=corr,
            payload={"stage": "classification"},
            status="failed",
            error_message=str(exc)[:2000],
            source="email_automation.pipeline",
        )
        return {
            "success": False,
            "error": "classification_failed",
            "parsed": parsed,
            "correlation_id": corr,
        }

    action_type = _determine_action(classification)
    class_payload = classification if isinstance(classification, dict) else {}

    record_email_event(
        user_id,
        "email.classified",
        provider="gmail",
        message_id=msg_id or None,
        thread_id=thread_id,
        lead_id=lead_id,
        correlation_id=corr,
        payload={
            "intent": class_payload.get("intent"),
            "confidence": class_payload.get("confidence"),
            "urgency": class_payload.get("urgency"),
            "classification_type": type(classification).__name__
            if not isinstance(classification, dict)
            else None,
        },
        status="applied",
        source="email_automation.pipeline",
    )

    record_email_event(
        user_id,
        "ai.action_recommended",
        provider="gmail",
        message_id=msg_id or None,
        thread_id=thread_id,
        lead_id=lead_id,
        correlation_id=corr,
        payload={"action_type": action_type, "intent": class_payload.get("intent")},
        status="applied",
        source="email_automation.pipeline",
    )

    safety = automation_safety_manager.check_rate_limits(
        user_id=user_id,
        action_type=action_type,
        target_contact=sender_email or "unknown",
    )
    if not (isinstance(safety, dict) and safety.get("allowed")):
        record_email_event(
            user_id,
            "ai.action_cancelled",
            provider="gmail",
            message_id=msg_id or None,
            thread_id=thread_id,
            lead_id=lead_id,
            correlation_id=corr,
            payload={"reason": "automation_safety", "action_type": action_type},
            status="failed",
            error_message="automation_blocked",
            source="email_automation.pipeline",
        )
        return {
            "success": False,
            "error": "automation_blocked",
            "details": safety if isinstance(safety, dict) else {"raw": str(safety)},
            "parsed": parsed,
            "classification": classification,
            "correlation_id": corr,
        }

    try:
        action_result = actions.process_email(
            parsed, action_type=action_type, user_id=user_id
        )
    except Exception as exc:
        logger.warning("process_email raised: %s", exc)
        record_email_event(
            user_id,
            "email.failed",
            provider="gmail",
            message_id=msg_id or None,
            thread_id=thread_id,
            lead_id=lead_id,
            correlation_id=corr,
            payload={"stage": "process_email", "action_type": action_type},
            status="failed",
            error_message=str(exc)[:2000],
            source="email_automation.pipeline",
        )
        return {
            "success": False,
            "error": "process_email_failed",
            "parsed": parsed,
            "classification": classification,
            "correlation_id": corr,
        }

    if not isinstance(action_result, dict):
        logger.warning(
            "process_email returned non-dict: %s", type(action_result).__name__
        )
        record_email_event(
            user_id,
            "email.failed",
            provider="gmail",
            message_id=msg_id or None,
            thread_id=thread_id,
            lead_id=lead_id,
            correlation_id=corr,
            payload={"stage": "process_email", "reason": "non_dict_result"},
            status="failed",
            error_message="invalid_action_result",
            source="email_automation.pipeline",
        )
        return {
            "success": False,
            "error": "invalid_action_result",
            "parsed": parsed,
            "classification": classification,
            "correlation_id": corr,
        }

    result_details = _action_result_details(action_result)

    # Log to CRM (activity) - skip if idempotent result
    try:
        if sender_email and not result_details.get("idempotent"):
            lead = db_optimizer.execute_query(
                "SELECT id FROM leads WHERE user_id = ? AND lower(email) = lower(?)",
                (user_id, sender_email),
            )
            if lead:
                enhanced_crm_service.add_lead_activity(
                    lead[0]["id"],
                    user_id,
                    "email_received",
                    f"Mailbox automation: {action_type}",
                    metadata={
                        "message_id": parsed.get("message_id"),
                        "intent": class_payload.get("intent"),
                        "action": action_type,
                        "success": action_result.get("success")
                    }
                )
    except Exception as e:
        logger.warning("Failed to log CRM activity: %s", e)

    if action_result.get("success", True):
        record_email_event(
            user_id,
            "ai.action_executed",
            provider="gmail",
            message_id=msg_id or None,
            thread_id=thread_id,
            lead_id=lead_id,
            correlation_id=corr,
            payload={
                "action": action_result.get("action"),
                "idempotent": result_details.get("idempotent"),
            },
            status="noop" if result_details.get("idempotent") else "applied",
            source="email_automation.pipeline",
        )
    else:
        _err = result_details.get("error") or action_result.get("error")
        if not _err and result_details.get("error_classification"):
            _err = str(result_details.get("error_classification"))
        record_email_event(
            user_id,
            "email.failed",
            provider="gmail",
            message_id=msg_id or None,
            thread_id=thread_id,
            lead_id=lead_id,
            correlation_id=corr,
            payload={
                "action": action_result.get("action"),
                "details_keys": list(result_details.keys()),
            },
            status="failed",
            error_message=str(_err or "action_failed")[:2000],
            source="email_automation.pipeline",
        )

    return {
        "success": action_result.get("success", True),
        "parsed": parsed,
        "classification": classification,
        "action": action_result,
        "correlation_id": corr,
    }
