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

from email_automation.parser import MinimalEmailParser
from email_automation.actions import MinimalEmailActions
from email_automation.service_manager import EmailServiceManager
from email_automation.jobs import EmailJobManager, EmailJob
from email_automation.ai_assistant import MinimalAIEmailAssistant
from core.automation_safety import automation_safety_manager
from core.database_optimization import db_optimizer
from crm.service import enhanced_crm_service
import logging

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


def parse_message(message: dict) -> dict:
    """Parse a raw message via the canonical parser."""
    parser = MinimalEmailParser()
    return parser.parse_message(message)


def process_incoming(message: dict, actions: MinimalEmailActions = None, user_id: int = None) -> dict:
    """
    Parse and optionally run actions on an incoming message.
    Caller can pass a configured MinimalEmailActions instance or None to only parse.
    """
    parsed = parse_message(message)
    if actions is None or user_id is None:
        return parsed
    return orchestrate_incoming(parsed, user_id=user_id, actions=actions)


def _determine_action(classification: dict) -> str:
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


def orchestrate_incoming(parsed: dict, user_id: int, actions: MinimalEmailActions = None) -> dict:
    """
    Full mailbox automation:
    parse -> classify -> decide action -> draft response -> execute action -> log to CRM
    """
    actions = actions or MinimalEmailActions(services={"ai_assistant": MinimalAIEmailAssistant()})

    parser = MinimalEmailParser()
    subject = parser.get_subject(parsed)
    body_text = parser.get_body_text(parsed) or parsed.get("snippet", "")
    from_header = parser.get_sender(parsed)
    sender_email = _extract_sender_email(from_header)

    ai_assistant = actions.services.get("ai_assistant") or MinimalAIEmailAssistant()
    classification = ai_assistant.classify_email_intent(body_text, subject)
    action_type = _determine_action(classification)

    # Safety gate
    safety = automation_safety_manager.check_rate_limits(
        user_id=user_id,
        action_type=action_type,
        target_contact=sender_email or "unknown"
    )
    if not safety.get("allowed"):
        return {
            "success": False,
            "error": "automation_blocked",
            "details": safety,
            "parsed": parsed,
            "classification": classification
        }

    action_result = actions.process_email(parsed, action_type=action_type, user_id=user_id)

    # Log to CRM (activity) - skip if idempotent result
    try:
        if sender_email and not (action_result.get("details", {}) or {}).get("idempotent"):
            lead = db_optimizer.execute_query(
                "SELECT id FROM leads WHERE user_id = ? AND email = ?",
                (user_id, sender_email)
            )
            if lead:
                enhanced_crm_service.add_lead_activity(
                    lead[0]["id"],
                    user_id,
                    "email_received",
                    f"Mailbox automation: {action_type}",
                    metadata={
                        "message_id": parsed.get("message_id"),
                        "intent": classification.get("intent"),
                        "action": action_type,
                        "success": action_result.get("success")
                    }
                )
    except Exception as e:
        logger.warning("Failed to log CRM activity: %s", e)

    return {
        "success": action_result.get("success", True),
        "parsed": parsed,
        "classification": classification,
        "action": action_result
    }
