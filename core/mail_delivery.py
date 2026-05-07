"""
Plain-text transactional email (SendGrid or SMTP).

Used when sending as the Gmail-connected user is not required (automations fallback).
Does not duplicate Flask route logic; callers must enforce auth and rate limits.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Any, Dict

logger = logging.getLogger(__name__)


def send_plain_text_transactional(to_email: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Send a UTF-8 plain-text message via SendGrid (if SENDGRID_API_KEY) or SMTP
    (SMTP_SERVER or SMTP_HOST, optional credentials).

    Returns:
        Dict with keys: success (bool), channel (str on attempt), optional error str,
        optional error_code (e.g. NO_MAIL_TRANSPORT).
    """
    to_email = (to_email or "").replace("\r", "").replace("\n", "").replace("\x00", "").strip()
    subject = (subject or "").replace("\r", "").replace("\n", "").replace("\x00", "")
    body = body or ""
    if not to_email or "@" not in to_email:
        return {
            "success": False,
            "error": "Invalid recipient email",
            "error_code": "INVALID_RECIPIENT",
            "channel": "none",
        }

    from_email = (
        os.getenv("FROM_EMAIL") or os.getenv("SMTP_USERNAME") or "noreply@localhost"
    )

    sendgrid_key = os.getenv("SENDGRID_API_KEY")
    if sendgrid_key:
        try:
            import sendgrid  # type: ignore
            from sendgrid.helpers.mail import Content, Mail  # type: ignore

            mail = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
            )
            mail.add_content(Content("text/plain", body))
            sg = sendgrid.SendGridAPIClient(api_key=sendgrid_key)
            sg.send(mail)
            logger.info("Transactional email sent via SendGrid to %s", to_email)
            return {"success": True, "channel": "sendgrid"}
        except Exception as exc:
            logger.warning("SendGrid transactional send failed: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "channel": "sendgrid",
            }

    smtp_server = os.getenv("SMTP_SERVER") or os.getenv("SMTP_HOST")
    if smtp_server:
        try:
            msg = EmailMessage()
            msg["From"] = from_email
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.set_content(body)
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USERNAME")
            smtp_pass = os.getenv("SMTP_PASSWORD")

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if smtp_user and smtp_pass:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            logger.info("Transactional email sent via SMTP to %s", to_email)
            return {"success": True, "channel": "smtp"}
        except Exception as exc:
            logger.warning("SMTP transactional send failed: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "channel": "smtp",
            }

    logger.info(
        "Transactional send skipped (no SENDGRID_API_KEY or SMTP_SERVER) recipient=%s",
        to_email,
    )
    return {
        "success": False,
        "error": "No email transport configured (SENDGRID_API_KEY or SMTP_SERVER).",
        "error_code": "NO_MAIL_TRANSPORT",
        "channel": "none",
    }
