"""Workflow follow-up scheduling and execution."""

import json
import logging
import hashlib
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from core.database_optimization import db_optimizer
from core.automation_run_events import record_automation_cancelled
from core.idempotency_manager import idempotency_manager
from core.automation_safety import automation_safety_manager
from core.sms_consent import lead_row_allows_sms
from crm.service import enhanced_crm_service

logger = logging.getLogger(__name__)


def schedule_follow_up(
    user_id: int,
    lead_id: Optional[int],
    follow_up_date: str,
    follow_up_type: str,
    message: str,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    follow_up_type = (follow_up_type or "email").lower()
    if follow_up_type not in {"email", "sms"}:
        logger.warning("Invalid follow_up_type=%s user_id=%s", follow_up_type, user_id)
        return {"success": False, "error": "Invalid follow_up_type"}

    corr = correlation_id or str(uuid.uuid4())

    existing = db_optimizer.execute_query(
        """
        SELECT id FROM scheduled_follow_ups
        WHERE user_id = ? AND lead_id IS ? AND follow_up_date = ? AND follow_up_type = ? AND message = ? AND status = 'scheduled'
        """,
        (user_id, lead_id, follow_up_date, follow_up_type, message)
    )
    if existing:
        logger.info("Deduped follow-up user_id=%s lead_id=%s type=%s date=%s", user_id, lead_id, follow_up_type, follow_up_date)
        try:
            from email_automation.email_event_log import record_email_event

            record_email_event(
                user_id,
                "email.followup_scheduled",
                lead_id=lead_id,
                correlation_id=corr,
                payload={
                    "follow_up_id": existing[0]["id"],
                    "follow_up_date": follow_up_date,
                    "follow_up_type": follow_up_type,
                    "deduped": True,
                },
                status="noop",
                source="workflow_followups",
            )
        except Exception:
            pass
        return {
            "success": True,
            "follow_up_id": existing[0]["id"],
            "deduped": True,
            "correlation_id": corr,
        }

    follow_up_id = db_optimizer.execute_insert_returning_id(
        """
        INSERT INTO scheduled_follow_ups
        (user_id, lead_id, follow_up_date, follow_up_type, message, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'scheduled', ?)
        """,
        (user_id, lead_id, follow_up_date, follow_up_type, message, datetime.utcnow().isoformat()),
    )

    logger.info("Scheduled follow-up id=%s user_id=%s lead_id=%s type=%s date=%s", follow_up_id, user_id, lead_id, follow_up_type, follow_up_date)
    try:
        from email_automation.email_event_log import record_email_event

        record_email_event(
            user_id,
            "email.followup_scheduled",
            lead_id=lead_id,
            correlation_id=corr,
            payload={
                "follow_up_id": follow_up_id,
                "follow_up_date": follow_up_date,
                "follow_up_type": follow_up_type,
            },
            status="applied",
            source="workflow_followups",
        )
    except Exception:
        pass
    return {
        "success": True,
        "follow_up_id": follow_up_id,
        "deduped": False,
        "correlation_id": corr,
    }


def _send_sms(user_id: int, lead_id: Optional[int], to_phone: str, message: str) -> Dict[str, Any]:
    """Send SMS via Twilio when configured. Returns {success, error?}. Logs to sms_messages."""
    to = str(to_phone).strip()
    if not to.startswith("+"):
        digits = "".join(c for c in to if c.isdigit())
        to = ("+" + digits) if (len(digits) == 11 and digits.startswith("1")) else ("+1" + digits) if len(digits) == 10 else ("+" + digits)
    status = "sent"
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
            logger.info("Twilio SMS sent to %s sid=%s user_id=%s", to, msg.sid, user_id)
        except Exception as e:
            status = "failed"
            error_msg = str(e)
            logger.exception("Twilio SMS error to %s user_id=%s", to, user_id)
    else:
        logger.warning("SMS skipped (Twilio not configured) to=%s user_id=%s", to, user_id)
        status = "skipped"
    try:
        db_optimizer.execute_query(
            """INSERT INTO sms_messages (user_id, lead_id, phone_number, message, status, sent_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, lead_id, to, message, status, datetime.utcnow().isoformat()),
            fetch=False,
        )
    except Exception as e:
        logger.warning("Failed to log SMS to sms_messages: %s", e)
    return {"success": status == "sent", "error": error_msg}


def _send_email(user_id: int, to_email: str, subject: str, body: str) -> Dict[str, Any]:
    """Send follow-up mail as the Gmail-connected user via shared Gmail client."""
    from integrations.gmail.gmail_client import gmail_client

    return gmail_client.send_plain_text_as_user(user_id, to_email, subject, body)


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
                # SMS follow-up via Twilio
                if not lead_id:
                    raise ValueError("lead_id required for sms follow-up")
                lead = db_optimizer.execute_query(
                    "SELECT id, phone, metadata FROM leads WHERE id = ? AND user_id = ?",
                    (lead_id, user_id)
                )
                if not lead or not lead[0].get("phone"):
                    raise ValueError("Lead phone not found")
                phone = lead[0]["phone"]
                target_contact = phone
                allowed, consent_reason = lead_row_allows_sms(lead[0])
                if not allowed:
                    logger.warning(
                        "SMS follow-up blocked (no consent) user_id=%s lead_id=%s reason=%s",
                        user_id,
                        lead_id,
                        consent_reason,
                    )
                    try:
                        db_optimizer.execute_query(
                            """INSERT INTO sms_messages (user_id, lead_id, phone_number, message, status, sent_at)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (
                                user_id,
                                lead_id,
                                phone,
                                message or "",
                                "blocked_no_consent",
                                datetime.utcnow().isoformat(),
                            ),
                            fetch=False,
                        )
                    except Exception as log_err:
                        logger.debug("sms_messages log skipped: %s", log_err)
                    result = {"success": False, "error": consent_reason}
                else:
                    safety = automation_safety_manager.check_rate_limits(
                        user_id=user_id,
                        action_type=f"follow_up_{follow_up_type}",
                        target_contact=target_contact or "unknown"
                    )
                    if not safety.get("allowed"):
                        logger.warning("SMS follow-up rate limited user_id=%s lead_id=%s", user_id, lead_id)
                        raise ValueError("automation_blocked")
                    result = _send_sms(user_id, lead_id, phone, message or "Follow-up reminder from Fikiri.")

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

            try:
                from email_automation.email_event_log import record_email_event

                fu_corr = f"followup:{user_id}:{follow_up_id}"
                if result.get("success"):
                    if follow_up_type == "email":
                        record_email_event(
                            user_id,
                            "email.reply_sent",
                            provider="gmail",
                            lead_id=lead_id,
                            correlation_id=fu_corr,
                            payload={
                                "channel": "scheduled_follow_up",
                                "follow_up_id": follow_up_id,
                                "gmail_message_id": result.get("message_id"),
                            },
                            status="applied",
                            source="workflow_followups",
                        )
                    else:
                        record_email_event(
                            user_id,
                            "ai.action_executed",
                            lead_id=lead_id,
                            correlation_id=fu_corr,
                            payload={
                                "channel": "scheduled_follow_up_sms",
                                "follow_up_id": follow_up_id,
                            },
                            status="applied",
                            source="workflow_followups",
                        )
                else:
                    record_email_event(
                        user_id,
                        "email.failed",
                        lead_id=lead_id,
                        correlation_id=fu_corr,
                        payload={
                            "channel": "scheduled_follow_up",
                            "follow_up_id": follow_up_id,
                            "follow_up_type": follow_up_type,
                        },
                        status="failed",
                        error_message=(result.get("error") or "follow_up_failed")[:2000],
                        source="workflow_followups",
                    )
            except Exception as ev_err:
                logger.debug("follow-up email_events: %s", ev_err)

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


def run_due_follow_ups_for_all_users(now_iso: Optional[str] = None) -> Dict[str, Any]:
    """Run due follow-ups for every user that has scheduled_follow_ups due. Called by the delivery scheduler."""
    now_iso = now_iso or datetime.utcnow().isoformat()
    rows = db_optimizer.execute_query(
        """
        SELECT DISTINCT user_id
        FROM scheduled_follow_ups
        WHERE status = 'scheduled' AND follow_up_date <= ?
        """,
        (now_iso,),
    )
    user_ids = [r["user_id"] for r in rows] if rows else []
    total_processed = 0
    total_failed = 0
    for uid in user_ids:
        try:
            result = execute_due_follow_ups(uid, now_iso=now_iso)
            total_processed += result.get("processed", 0)
            total_failed += result.get("failed", 0)
        except Exception as e:
            logger.exception("run_due_follow_ups_for_all_users user_id=%s error=%s", uid, e)
            total_failed += 1
    return {"success": True, "users_run": len(user_ids), "processed": total_processed, "failed": total_failed}


def process_due_calendar_reminders(now_iso: Optional[str] = None) -> Dict[str, Any]:
    """Mark due calendar_events as reminded and add lead_activity so they show up in CRM. No external calendar sync yet."""
    now_iso = now_iso or datetime.utcnow().isoformat()
    rows = db_optimizer.execute_query(
        """
        SELECT id, user_id, lead_id, title, event_date, description
        FROM calendar_events
        WHERE status = 'scheduled' AND event_date <= ?
        ORDER BY event_date ASC
        """,
        (now_iso,),
    )
    reminded = 0
    for row in rows:
        try:
            event_id = row["id"]
            user_id = row["user_id"]
            lead_id = row.get("lead_id")
            title = row.get("title") or "Calendar event"
            event_date = row.get("event_date", "")
            db_optimizer.execute_query(
                "UPDATE calendar_events SET status = ? WHERE id = ? AND user_id = ?",
                ("reminded", event_id, user_id),
                fetch=False,
            )
            if lead_id:
                enhanced_crm_service.add_lead_activity(
                    lead_id,
                    user_id,
                    "meeting_scheduled",
                    f"Reminder: {title} (scheduled {event_date})",
                    metadata={"calendar_event_id": event_id},
                )
            reminded += 1
        except Exception as e:
            logger.exception("process_due_calendar_reminders event_id=%s error=%s", row.get("id"), e)
    return {"success": True, "reminded": reminded}


def cancel_pending_work_for_lead(user_id: int, lead_id: int, reason: str = "withdrawn_by_client") -> Dict[str, Any]:
    """
    Stop non-terminal scheduled work for a lead without deleting history.
    Updates rows to terminal non-sendable statuses (cancelled / failed where applicable).
    """
    now = datetime.utcnow().isoformat()
    cancelled_scheduled = 0
    cancelled_tasks = 0
    cancelled_jobs = 0
    cancelled_calendar = 0

    try:
        pending_fu = db_optimizer.execute_query(
            """
            SELECT id FROM scheduled_follow_ups
            WHERE user_id = ? AND lead_id = ? AND status = 'scheduled'
            """,
            (user_id, lead_id),
        )
        cancelled_scheduled = db_optimizer.execute_query(
            """
            UPDATE scheduled_follow_ups
            SET status = 'cancelled', sent_at = COALESCE(sent_at, ?)
            WHERE user_id = ? AND lead_id = ? AND status = 'scheduled'
            """,
            (now, user_id, lead_id),
            fetch=False,
        ) or 0
        try:
            from email_automation.email_event_log import record_email_event

            cancel_corr = str(uuid.uuid4())
            for row in pending_fu or []:
                record_email_event(
                    user_id,
                    "email.followup_cancelled",
                    lead_id=lead_id,
                    correlation_id=cancel_corr,
                    payload={"follow_up_id": row["id"], "reason": reason},
                    status="applied",
                    source="workflow_followups",
                )
        except Exception as ev_err:
            logger.debug("followup_cancel events: %s", ev_err)
    except Exception as e:
        logger.warning("cancel scheduled_follow_ups user_id=%s lead_id=%s: %s", user_id, lead_id, e)

    try:
        cancelled_tasks = db_optimizer.execute_query(
            """
            UPDATE follow_up_tasks
            SET status = 'cancelled', updated_at = ?
            WHERE user_id = ? AND lead_id = ? AND status = 'pending'
            """,
            (now, user_id, lead_id),
            fetch=False,
        ) or 0
    except Exception as e:
        logger.warning("cancel follow_up_tasks user_id=%s lead_id=%s: %s", user_id, lead_id, e)

    try:
        rows = db_optimizer.execute_query(
            """
            SELECT job_id, payload_json, status
            FROM automation_jobs
            WHERE user_id = ? AND status IN ('queued', 'running', 'retrying')
            """,
            (user_id,),
        )
        for row in rows or []:
            try:
                payload = json.loads(row.get("payload_json") or "{}")
                trigger_data = payload.get("trigger_data") or {}
                job_lead = trigger_data.get("lead_id")
                if job_lead is None:
                    continue
                if int(job_lead) != int(lead_id):
                    continue
                db_optimizer.execute_query(
                    """
                    UPDATE automation_jobs
                    SET status = ?, completed_at = ?, error_message = ?
                    WHERE job_id = ?
                    """,
                    ("cancelled", now, reason, row["job_id"]),
                    fetch=False,
                )
                record_automation_cancelled(
                    user_id,
                    run_id=row["job_id"],
                    job_id=row["job_id"],
                    reason=reason,
                    lead_id=lead_id,
                )
                cancelled_jobs += 1
            except Exception as inner:
                logger.debug("Skip automation job %s: %s", row.get("job_id"), inner)
    except Exception as e:
        logger.warning("cancel automation_jobs user_id=%s lead_id=%s: %s", user_id, lead_id, e)

    try:
        cancelled_calendar = db_optimizer.execute_query(
            """
            UPDATE calendar_events
            SET status = 'cancelled'
            WHERE user_id = ? AND lead_id = ? AND status = 'scheduled'
            """,
            (user_id, lead_id),
            fetch=False,
        ) or 0
    except Exception as e:
        logger.warning("cancel calendar_events user_id=%s lead_id=%s: %s", user_id, lead_id, e)

    return {
        "success": True,
        "cancelled_scheduled_follow_ups": cancelled_scheduled,
        "cancelled_follow_up_tasks": cancelled_tasks,
        "cancelled_automation_jobs": cancelled_jobs,
        "cancelled_calendar_events": cancelled_calendar,
    }
