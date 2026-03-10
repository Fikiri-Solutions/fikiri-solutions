"""
Contact API - Public form submissions to info@fikirisolutions.com
UTF-8, strict text limits to keep cost and abuse low.
"""

import logging
import re
import os
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# Limits (chars) - feasible to avoid large payloads/cost
CONTACT_LIMITS = {
    "name": 200,
    "email": 254,
    "phone": 50,
    "company": 200,
    "subject": 200,
    "message": 3000,
}

CONTACT_TO_EMAIL = os.getenv("CONTACT_TO_EMAIL", "info@fikirisolutions.com")
CONTACT_FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@fikirisolutions.com")

contact_bp = Blueprint("contact", __name__, url_prefix="/api")


def _send_contact_email(to_email: str, subject: str, body_utf8: str) -> bool:
    """Send email via SendGrid or SMTP. Body must be UTF-8."""
    if not to_email or "@" not in to_email:
        return False
    try:
        if os.getenv("SENDGRID_API_KEY"):
            return _send_via_sendgrid(to_email, subject, body_utf8)
        if os.getenv("SMTP_SERVER"):
            return _send_via_smtp(to_email, subject, body_utf8)
        logger.info("Contact form: no mail provider configured, would send to %s", to_email)
        return False
    except Exception as e:
        logger.exception("Contact email send failed: %s", e)
        return False


def _send_via_sendgrid(to_email: str, subject: str, body: str) -> bool:
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail
        sg = sendgrid.SendGridAPIClient(api_key=os.getenv("SENDGRID_API_KEY"))
        mail = Mail(
            from_email=CONTACT_FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=body,
        )
        sg.send(mail)
        logger.info("Contact email sent via SendGrid to %s", to_email)
        return True
    except Exception as e:
        logger.error("SendGrid contact email failed: %s", e)
        return False


def _send_via_smtp(to_email: str, subject: str, body: str) -> bool:
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(body, "html", "utf-8")
        msg["Subject"] = subject
        msg["From"] = CONTACT_FROM_EMAIL
        msg["To"] = to_email
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USERNAME")
        smtp_pass = os.getenv("SMTP_PASSWORD")
        with smtplib.SMTP(smtp_server, smtp_port) as s:
            if smtp_user and smtp_pass:
                s.starttls()
                s.login(smtp_user, smtp_pass)
            s.sendmail(CONTACT_FROM_EMAIL, [to_email], msg.as_string())
        logger.info("Contact email sent via SMTP to %s", to_email)
        return True
    except Exception as e:
        logger.error("SMTP contact email failed: %s", e)
        return False


def _truncate(s: str, max_len: int) -> str:
    if s is None:
        return ""
    return (s.strip() or "")[:max_len]


def _validate_email(email: str) -> bool:
    if not email or len(email) > CONTACT_LIMITS["email"]:
        return False
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email))


@contact_bp.route("/contact", methods=["POST"])
def submit_contact():
    """
    Accept contact form: name, email, phone (optional), company (optional), subject (optional), message.
    UTF-8. Strict character limits. Sends to CONTACT_TO_EMAIL (default info@fikirisolutions.com).
    """
    if request.content_type and "application/json" in request.content_type:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form or {}

    name = _truncate(data.get("name") or "", CONTACT_LIMITS["name"])
    email = _truncate(data.get("email") or "", CONTACT_LIMITS["email"])
    phone = _truncate(data.get("phone") or "", CONTACT_LIMITS["phone"])
    company = _truncate(data.get("company") or "", CONTACT_LIMITS["company"])
    subject = _truncate(data.get("subject") or "", CONTACT_LIMITS["subject"])
    message = _truncate(data.get("message") or "", CONTACT_LIMITS["message"])

    if not name:
        return jsonify({"success": False, "error": "Name is required"}), 400
    if not _validate_email(email):
        return jsonify({"success": False, "error": "Valid email is required"}), 400
    if not message:
        return jsonify({"success": False, "error": "Message is required"}), 400

    email_subject = f"Contact form: {subject}" if subject else "Fikiri contact form submission"
    if len(email_subject) > 200:
        email_subject = email_subject[:197] + "..."

    lines = [
        f"<p><strong>Name:</strong> {name}</p>",
        f"<p><strong>Email:</strong> {email}</p>",
    ]
    if phone:
        lines.append(f"<p><strong>Phone:</strong> {phone}</p>")
    if company:
        lines.append(f"<p><strong>Company:</strong> {company}</p>")
    if subject:
        lines.append(f"<p><strong>Subject:</strong> {subject}</p>")
    lines.append("<p><strong>Message:</strong></p>")
    lines.append(f"<p>{message.replace(chr(10), '<br>')}</p>")
    body = "\n".join(lines)

    sent = _send_contact_email(CONTACT_TO_EMAIL, email_subject, body)
    if not sent:
        return jsonify({"success": False, "error": "Unable to send message. Please try again later."}), 503
    return jsonify({"success": True, "message": "Thank you. We will get back to you soon."}), 200
