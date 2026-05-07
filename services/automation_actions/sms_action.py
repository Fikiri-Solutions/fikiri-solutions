"""SMS automation action handler."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict

from core.database_optimization import db_optimizer


class SmsActionHandler:
    """Owns SEND_SMS execution details for automation rules."""

    def __init__(self, logger):
        self.logger = logger

    def execute_send_sms(
        self, action_data: Dict[str, Any], trigger_data: Dict[str, Any], user_id: int
    ) -> Dict[str, Any]:
        """Send SMS via Twilio when configured; requires lead_id and leads.metadata.sms_consent."""
        try:
            from core.sms_consent import lead_row_allows_sms, lead_sms_destination_matches

            lead_id = action_data.get("lead_id") or trigger_data.get("lead_id")
            phone_number = action_data.get("phone_number")
            message = action_data.get("message", "")
            if not lead_id:
                return {
                    "success": False,
                    "error": "lead_id required for SMS (consent is verified per lead)",
                    "error_code": "SMS_LEAD_REQUIRED",
                }
            if not message:
                return {"success": False, "error": "message required"}
            row = db_optimizer.execute_query(
                "SELECT id, phone, metadata FROM leads WHERE id = ? AND user_id = ?",
                (lead_id, user_id),
            )
            if not row:
                return {"success": False, "error": "Lead not found", "error_code": "LEAD_NOT_FOUND"}
            lead = row[0]
            ok, reason = lead_row_allows_sms(lead)
            if not ok:
                return {
                    "success": False,
                    "error": reason,
                    "error_code": "SMS_CONSENT_REQUIRED",
                }
            lead_phone = lead.get("phone") or ""
            if not str(lead_phone).strip():
                return {"success": False, "error": "Lead has no phone number"}
            if not lead_sms_destination_matches(lead_phone, phone_number):
                return {
                    "success": False,
                    "error": "phone_number does not match lead phone (consent applies to lead record only)",
                    "error_code": "SMS_PHONE_MISMATCH",
                }
            to = str(lead_phone).strip()
            if not to.startswith("+"):
                digits = "".join(c for c in to if c.isdigit())
                to = (
                    ("+" + digits)
                    if len(digits) == 11 and digits.startswith("1")
                    else ("+1" + digits)
                    if len(digits) == 10
                    else ("+" + digits)
                )
            status = "skipped"
            error_msg = None
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            messaging_sid = os.getenv("TWILIO_MESSAGING_SERVICE_SID")
            if account_sid and auth_token and messaging_sid:
                try:
                    from twilio.rest import Client

                    client = Client(account_sid, auth_token)
                    msg = client.messages.create(
                        messaging_service_sid=messaging_sid,
                        body=message,
                        to=to,
                    )
                    self.logger.info("Twilio SMS sent to %s sid=%s", to, msg.sid)
                    status = "sent"
                except Exception as e:
                    status = "failed"
                    error_msg = str(e)
                    self.logger.exception("Twilio SMS error to %s", to)
            else:
                self.logger.info("SMS (no Twilio): to=%s body=%s", to, message[:50])
            try:
                db_optimizer.execute_query(
                    """INSERT INTO sms_messages (user_id, lead_id, phone_number, message, status, sent_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (user_id, lead_id, to, message, status, datetime.now().isoformat()),
                    fetch=False,
                )
            except Exception:
                pass
            return {"success": status == "sent", "error": error_msg}
        except Exception as e:
            self.logger.error("Error sending SMS: %s", e)
            return {"success": False, "error": str(e)}
