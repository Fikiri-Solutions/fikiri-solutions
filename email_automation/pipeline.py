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
from core.email_pipeline_ai_gate import (
    evaluate_email_pipeline_ai_gate,
    record_email_pipeline_ai_usage,
    email_pipeline_ai_gate_enabled,
)
from crm.service import enhanced_crm_service
from services.email_capture_workflow import run_inbound_email_workflow
from core.ai.policies import evaluate_email_action_policy

__all__ = [
    "MinimalEmailParser",
    "MinimalEmailActions",
    "EmailServiceManager",
    "EmailJobManager",
    "EmailJob",
    "parse_message",
    "process_incoming",
    "orchestrate_incoming",
    "build_parsed_email_for_pipeline",
]

logger = logging.getLogger(__name__)


def build_parsed_email_for_pipeline(
    *,
    message_id: str,
    subject: str,
    from_header: str,
    body_text: str,
    snippet: str = "",
    thread_id: str = "",
    labels: Optional[list] = None,
) -> Dict[str, Any]:
    """Canonical parsed shape for ``orchestrate_incoming`` / ``MinimalEmailParser`` (headers lowercased)."""
    return {
        "message_id": message_id or "",
        "thread_id": thread_id or "",
        "headers": {
            "from": from_header or "",
            "subject": subject or "",
        },
        "body": {"text": body_text or "", "html": ""},
        "snippet": snippet or "",
        "labels": labels if isinstance(labels, list) else [],
        "attachments": [],
    }


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


def _load_thread_history(
    user_id: int,
    *,
    thread_id: Optional[str],
    sender_email: str,
    limit: int = 5,
) -> list:
    if not thread_id:
        return []
    try:
        rows = db_optimizer.execute_query(
            """
            SELECT sender, subject, SUBSTR(COALESCE(body, ''), 1, 500) AS body_preview, date
            FROM synced_emails
            WHERE user_id = ? AND thread_id = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (user_id, thread_id, limit),
        )
        if rows:
            return [dict(r) for r in rows]
    except Exception:
        pass
    if not sender_email:
        return []
    try:
        rows = db_optimizer.execute_query(
            """
            SELECT sender, subject, SUBSTR(COALESCE(body, ''), 1, 500) AS body_preview, date
            FROM synced_emails
            WHERE user_id = ? AND lower(sender) LIKE lower(?)
            ORDER BY date DESC
            LIMIT ?
            """,
            (user_id, f"%{sender_email}%", limit),
        )
        return [dict(r) for r in (rows or [])]
    except Exception:
        return []


def _load_crm_context(user_id: int, lead_id: Optional[int], sender_email: str) -> Dict[str, Any]:
    if lead_id:
        try:
            row = enhanced_crm_service.get_lead(lead_id, user_id)
            if row:
                return dict(row)
        except Exception:
            pass
    if not sender_email:
        return {}
    try:
        rows = db_optimizer.execute_query(
            """
            SELECT id, email, name, company, stage, score, tags, metadata
            FROM leads
            WHERE user_id = ? AND lower(email) = lower(?) AND withdrawn_at IS NULL
            LIMIT 1
            """,
            (user_id, sender_email),
        )
        if rows:
            return dict(rows[0])
    except Exception:
        pass
    return {}


def _apply_crm_recommendations(
    *,
    user_id: int,
    lead_id: Optional[int],
    analysis: Dict[str, Any],
    correlation_id: str,
) -> None:
    if not lead_id:
        return
    crm_updates = analysis.get("crm_updates")
    if not isinstance(crm_updates, dict):
        return
    update_payload = {
        "stage": crm_updates.get("stage"),
        "tags": crm_updates.get("tags"),
        "metadata": {
            "email_ai_priority": crm_updates.get("priority"),
            "email_follow_up_needed": bool(crm_updates.get("follow_up_needed")),
            "email_ai_intent": analysis.get("intent"),
            "correlation_id": correlation_id,
        },
        "correlation_id": correlation_id,
    }
    try:
        enhanced_crm_service.update_lead(lead_id, user_id, update_payload)
    except Exception as e:
        logger.warning("Failed to apply CRM recommendations: %s", e)


def orchestrate_incoming(
    parsed: dict,
    user_id: int,
    actions: MinimalEmailActions = None,
    trace_id: str = None,
    correlation_id: Optional[str] = None,
    *,
    synced_email_row_id: Optional[int] = None,
    external_message_id: Optional[str] = None,
    provider: str = "gmail",
    mailbox_owner_email: Optional[str] = None,
    run_mailbox_ai: bool = True,
) -> dict:
    """
    Inbound mailbox path (unified):
    run_inbound_email_workflow (lead + EMAIL_RECEIVED automations), then optionally
    classify -> decide action -> execute (Gmail-oriented handlers when AI enabled).
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

    inbound_workflow: Dict[str, Any]
    try:
        inbound_workflow = run_inbound_email_workflow(
            user_id,
            synced_email_row_id=synced_email_row_id,
            external_message_id=(external_message_id or msg_id or ""),
            sender_header=from_header or "",
            subject=subject or "",
            body_text=body_text,
            provider=provider,
            correlation_id=corr,
            mailbox_owner_email=mailbox_owner_email,
        )
    except Exception as exc:
        logger.warning("run_inbound_email_workflow failed in orchestrate_incoming: %s", exc)
        inbound_workflow = {
            "success": False,
            "correlation_id": corr,
            "lead_capture": {},
            "automation": {},
            "error": str(exc),
        }

    wf_lc = inbound_workflow.get("lead_capture") if isinstance(inbound_workflow, dict) else {}
    if isinstance(wf_lc, dict) and wf_lc.get("success"):
        wf_data = wf_lc.get("data")
        if isinstance(wf_data, dict) and wf_data.get("lead_id") is not None:
            try:
                lead_id = int(wf_data["lead_id"])
            except (TypeError, ValueError):
                pass

    if not run_mailbox_ai:
        return {
            "success": True,
            "parsed": parsed,
            "inbound_workflow": inbound_workflow,
            "correlation_id": corr,
            "mailbox_ai_skipped": True,
        }

    gate = evaluate_email_pipeline_ai_gate(user_id)
    if not gate.allowed:
        return {
            "success": True,
            "parsed": parsed,
            "inbound_workflow": inbound_workflow,
            "correlation_id": corr,
            "mailbox_ai_skipped": True,
            "mailbox_ai_skip_reason": gate.reason,
        }

    record_email_event(
        user_id,
        "email.parsed",
        provider=provider,
        message_id=msg_id or None,
        thread_id=thread_id,
        lead_id=lead_id,
        correlation_id=corr,
        payload={"subject": (subject or "")[:500]},
        status="applied",
        source="email_automation.pipeline",
    )

    ai_assistant = actions.services.get("ai_assistant") or MinimalAIEmailAssistant()
    thread_history = _load_thread_history(
        user_id,
        thread_id=thread_id,
        sender_email=sender_email,
    )
    crm_context = _load_crm_context(user_id, lead_id, sender_email)
    business_context = ai_assistant._load_business_context()
    try:
        analysis = ai_assistant.analyze_incoming_email(
            sender_email=sender_email,
            sender_name=from_header,
            subject=subject,
            body=body_text,
            thread_history=thread_history,
            crm_lead_data=crm_context,
            business_context=business_context,
            correlation_id=corr,
            user_id=user_id,
        )
    except Exception as exc:
        logger.warning("Email analysis failed: %s", exc)
        record_email_event(
            user_id,
            "email.failed",
            provider=provider,
            message_id=msg_id or None,
            thread_id=thread_id,
            lead_id=lead_id,
            correlation_id=corr,
            payload={"stage": "analysis"},
            status="failed",
            error_message=str(exc)[:2000],
            source="email_automation.pipeline",
        )
        return {
            "success": False,
            "error": "analysis_failed",
            "parsed": parsed,
            "inbound_workflow": inbound_workflow,
            "correlation_id": corr,
        }

    record_email_pipeline_ai_usage(user_id)

    analysis_payload = analysis if isinstance(analysis, dict) else {}
    policy_result = evaluate_email_action_policy(analysis_payload)
    action_type = policy_result.get("recommended_action_type", "auto_reply")
    _apply_crm_recommendations(
        user_id=user_id,
        lead_id=lead_id,
        analysis=analysis_payload,
        correlation_id=corr,
    )

    record_email_event(
        user_id,
        "email.analyzed",
        provider=provider,
        message_id=msg_id or None,
        thread_id=thread_id,
        lead_id=lead_id,
        correlation_id=corr,
        payload={
            "intent": analysis_payload.get("intent"),
            "confidence": analysis_payload.get("confidence"),
            "urgency": analysis_payload.get("urgency"),
            "business_value": analysis_payload.get("business_value"),
        },
        status="applied",
        source="email_automation.pipeline",
    )

    record_email_event(
        user_id,
        "email.classified",
        provider=provider,
        message_id=msg_id or None,
        thread_id=thread_id,
        lead_id=lead_id,
        correlation_id=corr,
        payload={
            "intent": analysis_payload.get("intent"),
            "confidence": analysis_payload.get("confidence"),
            "urgency": analysis_payload.get("urgency"),
        },
        status="applied",
        source="email_automation.pipeline",
    )

    record_email_event(
        user_id,
        "ai.action_recommended",
        provider=provider,
        message_id=msg_id or None,
        thread_id=thread_id,
        lead_id=lead_id,
        correlation_id=corr,
        payload={
            "action_type": action_type,
            "intent": analysis_payload.get("intent"),
            "execution_mode": policy_result.get("execution_mode"),
        },
        status="applied",
        source="email_automation.pipeline",
    )
    record_email_event(
        user_id,
        "ai.action.recommended",
        provider=provider,
        message_id=msg_id or None,
        thread_id=thread_id,
        lead_id=lead_id,
        correlation_id=corr,
        payload={
            "action_type": action_type,
            "intent": analysis_payload.get("intent"),
            "execution_mode": policy_result.get("execution_mode"),
        },
        status="applied",
        source="email_automation.pipeline",
    )
    record_email_event(
        user_id,
        "ai.policy.evaluated",
        provider=provider,
        message_id=msg_id or None,
        thread_id=thread_id,
        lead_id=lead_id,
        correlation_id=corr,
        payload={
            "schema_version": analysis_payload.get("schema_version"),
            "intent": policy_result.get("intent"),
            "execution_mode": policy_result.get("execution_mode"),
            "should_auto_send": policy_result.get("should_auto_send"),
            "requires_human_review": policy_result.get("requires_human_review"),
            "reason": policy_result.get("reason"),
        },
        status="applied",
        source="email_automation.pipeline",
    )

    should_auto_send = bool(policy_result.get("should_auto_send"))
    needs_human_review = bool(policy_result.get("requires_human_review"))
    suggested_reply = analysis_payload.get("suggested_reply")
    if suggested_reply:
        record_email_event(
            user_id,
            "email.reply_drafted",
            provider=provider,
            message_id=msg_id or None,
            thread_id=thread_id,
            lead_id=lead_id,
            correlation_id=corr,
            payload={
                "preview": str(suggested_reply)[:500],
                "needs_human_review": needs_human_review,
            },
            status="applied",
            source="email_automation.pipeline",
        )

    if not should_auto_send or needs_human_review:
        return {
            "success": True,
            "parsed": parsed,
            "classification": analysis_payload,
            "analysis": analysis_payload,
            "action": {
                "success": True,
                "action": "draft_only",
                "details": {
                    "should_auto_send": should_auto_send,
                    "needs_human_review": needs_human_review,
                    "reason_for_recommendation": policy_result.get("reason"),
                    "execution_mode": policy_result.get("execution_mode"),
                },
            },
            "inbound_workflow": inbound_workflow,
            "correlation_id": corr,
        }

    safety = automation_safety_manager.check_rate_limits(
        user_id=user_id,
        action_type=action_type,
        target_contact=sender_email or "unknown",
    )
    if not (isinstance(safety, dict) and safety.get("allowed")):
        record_email_event(
            user_id,
            "ai.action_cancelled",
            provider=provider,
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
            "classification": analysis_payload,
            "analysis": analysis_payload,
            "inbound_workflow": inbound_workflow,
            "correlation_id": corr,
        }

    if email_pipeline_ai_gate_enabled():
        gate_reply = evaluate_email_pipeline_ai_gate(user_id)
        if not gate_reply.allowed:
            logger.info(
                "email_pipeline_ai_gate: reply path blocked user_id=%s reason=%s",
                user_id,
                gate_reply.reason,
            )
            record_email_event(
                user_id,
                "ai.action_cancelled",
                provider=provider,
                message_id=msg_id or None,
                thread_id=thread_id,
                lead_id=lead_id,
                correlation_id=corr,
                payload={
                    "reason": "mailbox_ai_gate_reply",
                    "action_type": action_type,
                    "code": gate_reply.reason,
                },
                status="failed",
                error_message="mailbox_ai_reply_gated",
                source="email_automation.pipeline",
            )
            return {
                "success": True,
                "parsed": parsed,
                "classification": analysis_payload,
                "analysis": analysis_payload,
                "action": {
                    "success": True,
                    "action": "draft_only",
                    "details": {
                        "should_auto_send": should_auto_send,
                        "needs_human_review": needs_human_review,
                        "reason_for_recommendation": policy_result.get("reason"),
                        "execution_mode": policy_result.get("execution_mode"),
                        "mailbox_ai_reply_skip_reason": gate_reply.reason,
                    },
                },
                "inbound_workflow": inbound_workflow,
                "correlation_id": corr,
                "mailbox_ai_reply_skipped": True,
                "mailbox_ai_reply_skip_reason": gate_reply.reason,
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
            provider=provider,
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
            "classification": analysis_payload,
            "analysis": analysis_payload,
            "inbound_workflow": inbound_workflow,
            "correlation_id": corr,
        }

    if not isinstance(action_result, dict):
        logger.warning(
            "process_email returned non-dict: %s", type(action_result).__name__
        )
        record_email_event(
            user_id,
            "email.failed",
            provider=provider,
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
            "classification": analysis_payload,
            "analysis": analysis_payload,
            "inbound_workflow": inbound_workflow,
            "correlation_id": corr,
        }

    result_details = _action_result_details(action_result)

    if (
        email_pipeline_ai_gate_enabled()
        and user_id
        and isinstance(ai_assistant, MinimalAIEmailAssistant)
        and ai_assistant.is_enabled()
        and action_type == "auto_reply"
        and action_result.get("success", True)
    ):
        record_email_pipeline_ai_usage(user_id, 1)

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
                        "intent": analysis_payload.get("intent"),
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
            provider=provider,
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
            provider=provider,
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
        "classification": analysis_payload,
        "analysis": analysis_payload,
        "action": action_result,
        "inbound_workflow": inbound_workflow,
        "correlation_id": corr,
    }
