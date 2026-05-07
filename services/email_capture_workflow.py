"""
Unified Email → Lead (CRM) → Automation workflow.

Invoked by ``email_automation.pipeline.orchestrate_incoming`` for every inbound path
(Gmail sync, Outlook sync, and mailbox AI orchestration after parsing). Ensures a
deterministic lead upsert, injects correlation_id + lead_id into trigger_data,
then executes EMAIL_RECEIVED rules (update_crm_field, trigger_webhook,
send_email, etc.).
"""

from __future__ import annotations

import logging
import uuid
from email.utils import parseaddr
from typing import Any, Dict, Optional

from crm.service import enhanced_crm_service
from services.automation_engine import automation_engine, TriggerType

logger = logging.getLogger(__name__)


def run_inbound_email_workflow(
    user_id: int,
    *,
    synced_email_row_id: Optional[int],
    external_message_id: str,
    sender_header: str,
    subject: str,
    body_text: str,
    provider: str,
    correlation_id: Optional[str] = None,
    mailbox_owner_email: Optional[str] = None,
) -> Dict[str, Any]:
    """
    correlation_id: propagated into CRM events, automation run context, and webhook payloads.
    """
    corr = correlation_id or str(uuid.uuid4())
    lead_res = enhanced_crm_service.upsert_lead_from_inbound_email(
        user_id,
        sender_header=sender_header,
        subject=subject,
        provider=provider,
        correlation_id=corr,
        mailbox_owner_email=mailbox_owner_email,
        default_source="gmail" if provider == "gmail" else "outlook",
    )

    disp_name, addr = parseaddr(sender_header or "")
    parsed_email = (addr or "").strip()
    sender_display = disp_name.strip() if disp_name else ""

    trigger: Dict[str, Any] = {
        "email_id": external_message_id,
        "synced_email_id": synced_email_row_id,
        "sender_email": parsed_email if parsed_email else (sender_header or ""),
        "sender_raw": sender_header,
        "sender_name": sender_display or (parsed_email.split("@")[0] if "@" in parsed_email else ""),
        "subject": subject or "",
        "text": body_text or "",
        "correlation_id": corr,
        "event_type": "email_received",
        "provider": provider,
    }
    lid = (
        lead_res.get("data", {}).get("lead_id")
        if isinstance(lead_res.get("data"), dict)
        else None
    )
    if lid is not None and lead_res.get("success") and not lead_res.get("skipped"):
        trigger["lead_id"] = int(lid)

    try:
        logger.info(
            "inbound_email_workflow user=%s provider=%s correlation_id=%s lead_capture=%s",
            user_id,
            provider,
            corr,
            "ok" if lead_res.get("success") else lead_res.get("error"),
        )
    except Exception:
        pass

    auto = automation_engine.execute_automation_rules(
        TriggerType.EMAIL_RECEIVED,
        trigger,
        user_id,
        automation_source=f"{provider}_inbound_workflow",
    )
    out: Dict[str, Any] = {
        "success": bool(auto.get("success")),
        "correlation_id": corr,
        "lead_capture": lead_res,
        "automation": auto,
    }
    return out
