"""Email automation action handler."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from core.automation_run_events import get_automation_run_id
from core.automation_safety import automation_safety_manager
from core.database_optimization import db_optimizer
from core.mail_delivery import send_plain_text_transactional
from core.workflow_followups import schedule_follow_up as workflow_schedule_follow_up
from crm.service import enhanced_crm_service
from integrations.gmail.gmail_client import gmail_client


class EmailActionHandler:
    """Owns SEND_EMAIL execution details for automation rules."""

    def __init__(self, logger):
        self.logger = logger

    def parse_email_address(self, raw: Optional[str]) -> str:
        import re

        raw = (raw or "").replace("\r", "").replace("\n", "").replace("\x00", "").strip()
        if not raw:
            return ""
        if "," in raw or ";" in raw:
            return ""
        if "<" in raw and ">" in raw:
            match = re.search(r"<([^<>]+@[^<>]+)>", raw)
            if match:
                addr = match.group(1).strip().lower()
                return addr if "," not in addr else ""
        single = raw.strip().lower()
        return single if "," not in single else ""

    def sanitize_email_subject(self, subject: str) -> str:
        """Strip control chars disallowed in Subject headers."""
        s = (subject or "").replace("\r", "").replace("\n", "").replace("\x00", "")
        return s.strip()

    def delayed_email_recipient_mismatch_message(
        self, user_id: int, lead_id: int, expected_to: str
    ) -> Optional[str]:
        """
        scheduled_follow_ups email delivery sends to CRM lead.email only.
        Refuse scheduling when an explicit automation recipient does not match that row.
        """
        rows = db_optimizer.execute_query(
            "SELECT email FROM leads WHERE id = ? AND user_id = ?",
            (int(lead_id), user_id),
        )
        if not rows:
            return "Lead not found for delayed send."
        lead_email = self.parse_email_address(rows[0].get("email"))
        if not lead_email:
            return "Lead has no valid email for delayed send."
        if lead_email != expected_to:
            return (
                "scheduled_follow_ups email uses CRM lead.email; "
                f"lead email is {lead_email!r}, but this action recipient is {expected_to!r}. "
                "Align `to` with the CRM lead email or omit `to` to use the inbound sender."
            )
        return None

    def send_email_idempotency_key(
        self,
        user_id: int,
        rule_id: int,
        to_email: str,
        subject: str,
        body: str,
        trigger_data: Dict[str, Any],
    ) -> str:
        run_fragment = get_automation_run_id() or ""
        body_fp = hashlib.sha256(body.encode("utf-8")).hexdigest()
        email_key = trigger_data.get("email_id")
        email_key_str = str(email_key) if email_key is not None else ""
        corr = str(trigger_data.get("correlation_id") or "")
        canonical = "|".join(
            [
                "send_email",
                str(user_id),
                str(rule_id),
                to_email,
                subject,
                body_fp,
                email_key_str,
                corr,
                run_fragment,
            ]
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def execute_send_email(
        self, parameters: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int
    ) -> Dict[str, Any]:
        """
        Send an outbound automation email.
        Recipient: ``to`` in parameters, else inbound ``sender_email`` from trigger_data.
        When ``delay_minutes`` > 0, schedules ``scheduled_follow_ups`` for email (requires ``lead_id``).
        Transport: Gmail (user OAuth) first, then SendGrid/SMTP.
        """
        delay_minutes = parameters.get("delay_minutes") or 0
        try:
            delay_minutes = max(0, int(delay_minutes))
        except (TypeError, ValueError):
            delay_minutes = 0

        to_email = self.parse_email_address(parameters.get("to")) or self.parse_email_address(
            trigger_data.get("sender_email")
        )
        subject = (
            self.sanitize_email_subject(
                parameters.get("subject") or parameters.get("title") or "Re: your message"
            )
            or "Follow-up"
        )
        body_raw = parameters.get("body") or parameters.get("message") or parameters.get("text")
        if not body_raw and parameters.get("template"):
            body_raw = (
                f"Thanks for your message"
                f"{(' (' + str(parameters.get('template')) + ')') if parameters.get('template') else ''}."
            )
        body = (body_raw or "Thanks for reaching out — we will get back to you shortly.").strip()
        subject = subject[:500]
        body = body[:20000]

        if not to_email or "@" not in to_email:
            return {
                "success": False,
                "error": "Missing recipient: set action ``to`` or use a trigger with sender_email.",
                "error_code": "MISSING_RECIPIENT",
            }

        if delay_minutes > 0:
            lead_id = trigger_data.get("lead_id")
            if lead_id is None:
                return {
                    "success": False,
                    "error": "delay_minutes requires lead_id (e.g. from an earlier update_crm_field rule).",
                    "error_code": "MISSING_LEAD_ID",
                }
            safety_delayed = automation_safety_manager.check_rate_limits(
                user_id=user_id,
                action_type="auto_reply",
                target_contact=to_email,
            )
            if not safety_delayed.get("allowed"):
                return {
                    "success": False,
                    "error": safety_delayed.get("message")
                    or "Rate limit or kill-switch blocked scheduled send",
                    "error_code": "AUTOMATION_BLOCKED",
                }
            mismatch = self.delayed_email_recipient_mismatch_message(user_id, int(lead_id), to_email)
            if mismatch:
                return {
                    "success": False,
                    "error": mismatch,
                    "error_code": "DELAYED_SEND_RECIPIENT_MISMATCH",
                }
            follow_up_date = (datetime.utcnow() + timedelta(minutes=delay_minutes)).isoformat()
            sched = workflow_schedule_follow_up(
                user_id,
                int(lead_id),
                follow_up_date,
                "email",
                body,
                correlation_id=trigger_data.get("correlation_id"),
            )
            if not sched.get("success"):
                return sched
            return {
                "success": True,
                "data": {
                    "action": "email_scheduled",
                    "recipient": to_email,
                    "follow_up_id": sched.get("follow_up_id"),
                    "delay_minutes": delay_minutes,
                },
            }

        safety = automation_safety_manager.check_rate_limits(
            user_id=user_id,
            action_type="auto_reply",
            target_contact=to_email,
        )
        if not safety.get("allowed"):
            return {
                "success": False,
                "error": safety.get("message") or "Rate limit or kill-switch blocked send",
                "error_code": "AUTOMATION_BLOCKED",
            }

        rule_id = int(trigger_data.get("_automation_rule_id") or 0)
        idempotency_key = self.send_email_idempotency_key(
            user_id, rule_id, to_email, subject, body, trigger_data
        )

        send_result = gmail_client.send_plain_text_as_user(user_id, to_email, subject, body)
        if not send_result.get("success"):
            send_result = send_plain_text_transactional(to_email, subject, body)

        automation_safety_manager.log_automation_action(
            user_id=user_id,
            rule_id=rule_id,
            action_type="auto_reply",
            target_contact=to_email,
            idempotency_key=idempotency_key,
            status="completed" if send_result.get("success") else "failed",
            error_message=None if send_result.get("success") else send_result.get("error"),
        )

        if not send_result.get("success"):
            return {
                "success": False,
                "error": send_result.get("error") or "Send failed",
                "error_code": send_result.get("error_code") or "SEND_FAILED",
            }

        lead_id = trigger_data.get("lead_id")
        if lead_id is not None:
            try:
                enhanced_crm_service.add_lead_activity(
                    int(lead_id),
                    user_id,
                    "email_sent",
                    f"Automation email sent: {subject[:120]}",
                    metadata={"channel": send_result.get("channel"), "to": to_email},
                )
            except Exception as act_err:
                self.logger.debug("add_lead_activity after automation send: %s", act_err)

        try:
            from email_automation.email_event_log import record_email_event

            record_email_event(
                user_id,
                "email.reply_sent",
                provider=send_result.get("channel") or "automation",
                lead_id=int(lead_id) if lead_id is not None else None,
                correlation_id=trigger_data.get("correlation_id"),
                payload={
                    "rule_id": rule_id,
                    "to": to_email,
                    "subject": subject,
                    "message_id": send_result.get("message_id"),
                    "gmail_message_id": send_result.get("message_id"),
                },
                status="applied",
                source="automation_engine",
            )
        except Exception as ev_err:
            self.logger.debug("automation send email_event: %s", ev_err)

        return {
            "success": True,
            "data": {
                "action": "email_sent",
                "recipient": to_email,
                "subject": subject,
                "template": parameters.get("template"),
                "channel": send_result.get("channel"),
                "message_id": send_result.get("message_id"),
            },
        }
