"""Workflow follow-up scheduling and execution."""

import base64
import json
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

from core.database_optimization import db_optimizer
from core.idempotency_manager import idempotency_manager
from core.automation_safety import automation_safety_manager
from core.oauth_token_manager import oauth_token_manager
from crm.service import enhanced_crm_service

logger = logging.getLogger(__name__)


def schedule_follow_up(user_id: int, lead_id: Optional[int], follow_up_date: str, follow_up_type: str, message: str) -> Dict[str, Any]:
    follow_up_type = (follow_up_type or "email").lower()
    if follow_up_type not in {"email", "sms"}:
        logger.warning("Invalid follow_up_type=%s user_id=%s", follow_up_type, user_id)
        return {"success": False, "error": "Invalid follow_up_type"}

    existing = db_optimizer.execute_query(
        """
        SELECT id FROM scheduled_follow_ups
        WHERE user_id = ? AND lead_id IS ? AND follow_up_date = ? AND follow_up_type = ? AND message = ? AND status = 'scheduled'
        """,
        (user_id, lead_id, follow_up_date, follow_up_type, message)
    )
    if existing:
        logger.info("Deduped follow-up user_id=%s lead_id=%s type=%s date=%s", user_id, lead_id, follow_up_type, follow_up_date)
        return {"success": True, "follow_up_id": existing[0]["id"], "deduped": True}

    follow_up_id = db_optimizer.execute_query(
        """
        INSERT INTO scheduled_follow_ups
        (user_id, lead_id, follow_up_date, follow_up_type, message, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'scheduled', ?)
        """,
        (user_id, lead_id, follow_up_date, follow_up_type, message, datetime.utcnow().isoformat()),
        fetch=False
    )

    logger.info("Scheduled follow-up id=%s user_id=%s lead_id=%s type=%s date=%s", follow_up_id, user_id, lead_id, follow_up_type, follow_up_date)
    return {"success": True, "follow_up_id": follow_up_id, "deduped": False}


def _send_email(user_id: int, to_email: str, subject: str, body: str) -> Dict[str, Any]:
    token_status = oauth_token_manager.get_token_status(user_id, "gmail")
    if not token_status.get('success') or not token_status.get('has_token'):
        logger.warning("Gmail token missing user_id=%s", user_id)
        return {"success": False, "error": "Gmail connection required"}

    try:
        from integrations.gmail.gmail_client import gmail_client
        gmail_service = gmail_client.get_gmail_service_for_user(user_id)
        message = {
            'raw': base64.urlsafe_b64encode(
                f"To: {to_email}\r\n"
                f"Subject: {subject}\r\n"
                f"Content-Type: text/plain; charset=UTF-8\r\n"
                f"\r\n"
                f"{body}".encode('utf-8')
            ).decode('utf-8')
        }
        sent_message = gmail_service.users().messages().send(
            userId='me', body=message
        ).execute()
        logger.info("Sent follow-up email user_id=%s message_id=%s", user_id, sent_message.get("id"))
        return {"success": True, "message_id": sent_message.get("id"), "thread_id": sent_message.get("threadId")}
    except Exception as e:
        logger.error("Follow-up email send failed user_id=%s error=%s", user_id, e)
        return {"success": False, "error": str(e)}


def execute_due_follow_ups(user_id: int, now_iso: Optional[str] = None) -> Dict[str, Any]:
    now_iso = now_iso or datetime.utcnow().isoformat()
    follow_ups = db_optimizer.execute_query(
        """
        SELECT id, user_id, lead_id, follow_up_date, follow_up_type, message
        FROM scheduled_follow_ups
        WHERE user_id = ? AND status = 'scheduled' AND follow_up_date <= ?
        ORDER BY follow_up_date ASC
        """,
        (user_id, now_iso)
    )

    processed = 0
    failed = 0

    for item in follow_ups:
        follow_up_id = item["id"]
        follow_up_type = item.get("follow_up_type", "email")
        lead_id = item.get("lead_id")
        message = item.get("message") or ""

        key = hashlib.sha256(
            f"workflow_followup|{user_id}|{follow_up_id}|{follow_up_type}".encode("utf-8")
        ).hexdigest()
        cached = idempotency_manager.check_key(key)
        if cached and cached.get("status") == "completed":
            logger.info("Skipping already processed follow-up id=%s user_id=%s", follow_up_id, user_id)
            continue
        idempotency_manager.store_key(key, "workflow_followup", user_id, {"follow_up_id": follow_up_id})

        target_contact = ""
        result = {"success": False}
        try:
            if follow_up_type == "email":
                if not lead_id:
                    raise ValueError("lead_id required for email follow-up")
                lead = db_optimizer.execute_query(
                    "SELECT id, email, name FROM leads WHERE id = ? AND user_id = ?",
                    (lead_id, user_id)
                )
                if not lead:
                    raise ValueError("Lead not found")
                to_email = lead[0]["email"]
                target_contact = to_email
                safety = automation_safety_manager.check_rate_limits(
                    user_id=user_id,
                    action_type=f"follow_up_{follow_up_type}",
                    target_contact=target_contact or "unknown"
                )
                if not safety.get("allowed"):
                    logger.warning("Follow-up rate limited user_id=%s lead_id=%s", user_id, lead_id)
                    raise ValueError("automation_blocked")
                subject = "Follow-up"
                body = message or "Just checking in to see if you have any questions."
                result = _send_email(user_id, to_email, subject, body)
            else:
                # SMS follow-up (logged only)
                if not lead_id:
                    raise ValueError("lead_id required for sms follow-up")
                lead = db_optimizer.execute_query(
                    "SELECT id, phone FROM leads WHERE id = ? AND user_id = ?",
                    (lead_id, user_id)
                )
                if not lead or not lead[0].get("phone"):
                    raise ValueError("Lead phone not found")
                phone = lead[0]["phone"]
                target_contact = phone
                safety = automation_safety_manager.check_rate_limits(
                    user_id=user_id,
                    action_type=f"follow_up_{follow_up_type}",
                    target_contact=target_contact or "unknown"
                )
                if not safety.get("allowed"):
                    logger.warning("SMS follow-up rate limited user_id=%s lead_id=%s", user_id, lead_id)
                    raise ValueError("automation_blocked")
                db_optimizer.execute_query(
                    """
                    INSERT INTO sms_messages (user_id, lead_id, phone_number, message, status, sent_at)
                    VALUES (?, ?, ?, ?, 'sent', ?)
                    """,
                    (user_id, lead_id, phone, message, datetime.utcnow().isoformat()),
                    fetch=False
                )
                result = {"success": True}

            logger.info("Executed follow-up id=%s user_id=%s type=%s success=%s", follow_up_id, user_id, follow_up_type, result.get("success"))
            status = "completed" if result.get("success") else "failed"
            idempotency_manager.update_key_result(key, status, result)

            db_optimizer.execute_query(
                """
                UPDATE scheduled_follow_ups
                SET status = ?, sent_at = ?
                WHERE id = ?
                """,
                ("sent" if result.get("success") else "failed", datetime.utcnow().isoformat(), follow_up_id),
                fetch=False
            )

            if lead_id:
                enhanced_crm_service.add_lead_activity(
                    lead_id,
                    user_id,
                    "follow_up",
                    f"Workflow follow-up sent ({follow_up_type})",
                    metadata={"follow_up_id": follow_up_id, "result": result}
                )

            automation_safety_manager.log_automation_action(
                user_id=user_id,
                rule_id=0,
                action_type=f"follow_up_{follow_up_type}",
                target_contact=target_contact or "unknown",
                idempotency_key=key,
                status="completed" if result.get("success") else "failed",
                error_message=None if result.get("success") else result.get("error")
            )

            if result.get("success"):
                processed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error("Follow-up execution failed id=%s user_id=%s error=%s", follow_up_id, user_id, e)
            idempotency_manager.update_key_result(key, "failed", {"success": False, "error": str(e)})
            db_optimizer.execute_query(
                "UPDATE scheduled_follow_ups SET status = ?, sent_at = ? WHERE id = ?",
                ("failed", datetime.utcnow().isoformat(), follow_up_id),
                fetch=False
            )
            automation_safety_manager.log_automation_action(
                user_id=user_id,
                rule_id=0,
                action_type=f"follow_up_{follow_up_type}",
                target_contact=target_contact or "unknown",
                idempotency_key=key,
                status="failed",
                error_message=str(e)
            )
            failed += 1

    return {"success": True, "processed": processed, "failed": failed}
