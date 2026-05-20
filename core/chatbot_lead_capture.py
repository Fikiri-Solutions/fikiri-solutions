"""
Chatbot widget lead capture — extract contact info and hand off to CRM.

Used by the public chatbot API only; dashboard preview does not create leads.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from core.chatbot_config import ChatbotConfig
from core.database_optimization import db_optimizer
from crm.service import enhanced_crm_service

logger = logging.getLogger(__name__)


def extract_lead_info(query: str, lead_payload: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Parse email, phone, and name from explicit payload or query text."""
    email = (lead_payload.get("email") or "").strip()
    phone = (lead_payload.get("phone") or "").strip()
    name = (lead_payload.get("name") or "").strip()

    if not email:
        match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", query)
        email = match.group(0) if match else ""
    if not phone:
        match = re.search(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", query)
        phone = match.group(0) if match else ""
    if not name and email:
        name = email.split("@")[0].replace(".", " ").title()

    return {
        "email": email or None,
        "phone": phone or None,
        "name": name or "Chatbot Lead",
    }


def _filter_collect_fields(
    lead_info: Dict[str, Optional[str]],
    chatbot_config: Optional[ChatbotConfig],
) -> Dict[str, Optional[str]]:
    if chatbot_config is None:
        return lead_info

    filtered = dict(lead_info)
    if not chatbot_config.collect_email:
        filtered["email"] = None
    if not chatbot_config.collect_phone:
        filtered["phone"] = None
    return filtered


def _skip_reason_no_contact(
    raw_info: Dict[str, Optional[str]],
    chatbot_config: Optional[ChatbotConfig],
) -> str:
    if chatbot_config and raw_info.get("email") and not chatbot_config.collect_email:
        return "collect_email_disabled"
    if chatbot_config and raw_info.get("phone") and not chatbot_config.collect_phone:
        return "collect_phone_disabled"
    return "no_contact_info"


def _conversation_id_present(conversation_id: Optional[str]) -> bool:
    return bool((conversation_id or "").strip())


def _log_lead_capture_skipped(
    *,
    reason: str,
    user_id: Optional[int],
    tenant_id: Optional[str],
    conversation_id: Optional[str],
) -> None:
    logger.info(
        "chatbot lead capture skipped",
        extra={
            "event": "chatbot.lead_capture.skipped",
            "service": "chatbot",
            "severity": "INFO",
            "reason": reason,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "conversation_id_present": _conversation_id_present(conversation_id),
        },
    )


def _log_lead_capture_completed(
    *,
    user_id: int,
    tenant_id: Optional[str],
    lead_id: int,
    created: bool,
    has_email: bool,
    has_phone: bool,
    conversation_id: Optional[str],
) -> None:
    logger.info(
        "chatbot lead capture completed",
        extra={
            "event": "chatbot.lead_capture.completed",
            "service": "chatbot",
            "severity": "INFO",
            "user_id": user_id,
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "created": created,
            "has_email": has_email,
            "has_phone": has_phone,
            "conversation_id_present": _conversation_id_present(conversation_id),
        },
    )


def _log_lead_capture_failed(
    *,
    user_id: int,
    tenant_id: Optional[str],
    error_type: str,
    conversation_id: Optional[str],
) -> None:
    logger.warning(
        "chatbot lead capture failed",
        extra={
            "event": "chatbot.lead_capture.failed",
            "service": "chatbot",
            "severity": "WARN",
            "user_id": user_id,
            "tenant_id": tenant_id,
            "error_type": error_type,
            "conversation_id_present": _conversation_id_present(conversation_id),
        },
    )


def capture_chatbot_lead(
    *,
    user_id: Optional[int],
    query: str,
    lead_payload: Dict[str, Any],
    conversation_id: str,
    tenant_id: Optional[str],
    chatbot_config: Optional[ChatbotConfig] = None,
) -> Optional[int]:
    """
    Extract lead contact info and create or reuse a CRM lead for the widget path.

    Returns lead_id when a lead is found or created; None otherwise.
    CRM failures are logged and do not propagate.
    """
    if not user_id:
        return None

    if chatbot_config is not None and not chatbot_config.lead_capture_enabled:
        _log_lead_capture_skipped(
            reason="disabled_by_config",
            user_id=user_id,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
        )
        return None

    raw_info = extract_lead_info(query, lead_payload)
    lead_info = _filter_collect_fields(raw_info, chatbot_config)
    if not (lead_info.get("email") or lead_info.get("phone")):
        _log_lead_capture_skipped(
            reason=_skip_reason_no_contact(raw_info, chatbot_config),
            user_id=user_id,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
        )
        return None

    lead_id: Optional[int] = None
    created = False
    try:
        if lead_info.get("email"):
            existing = db_optimizer.execute_query(
                "SELECT id FROM leads WHERE user_id = ? AND email = ?",
                (user_id, lead_info["email"]),
            )
            if existing:
                lead_id = existing[0]["id"]
                created = False
            else:
                created_result = enhanced_crm_service.create_lead(
                    user_id,
                    {
                        "email": lead_info["email"],
                        "name": lead_info.get("name") or "Chatbot Lead",
                        "phone": lead_info.get("phone"),
                        "source": "chatbot_widget",
                        "metadata": {
                            "conversation_id": conversation_id,
                            "tenant_id": tenant_id,
                        },
                    },
                )
                lead_id = (
                    created_result.get("data", {}).get("lead_id")
                    if created_result.get("success")
                    else None
                )
                created = lead_id is not None
        if lead_id:
            enhanced_crm_service.add_lead_activity(
                lead_id,
                user_id,
                "note_added",
                "Chatbot conversation captured lead info",
                metadata={"conversation_id": conversation_id, "query": query},
            )
            _log_lead_capture_completed(
                user_id=user_id,
                tenant_id=tenant_id,
                lead_id=lead_id,
                created=created,
                has_email=bool(lead_info.get("email")),
                has_phone=bool(lead_info.get("phone")),
                conversation_id=conversation_id,
            )
    except Exception as lead_error:
        _log_lead_capture_failed(
            user_id=user_id,
            tenant_id=tenant_id,
            error_type=type(lead_error).__name__,
            conversation_id=conversation_id,
        )
        return None

    return lead_id
