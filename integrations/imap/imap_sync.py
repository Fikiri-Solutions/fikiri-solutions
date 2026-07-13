"""Sync Yahoo, Apple iCloud, and other IMAP mailboxes into synced_emails."""

from __future__ import annotations

import email
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from core.database_optimization import db_optimizer
from core.imap_mail_helpers import (
    connect_imap,
    extract_attachments_from_imap_message,
    extract_body_from_imap_message,
    fetch_imap_rfc822,
    get_user_imap_settings,
    infer_provider_from_imap_settings,
    parse_imap_message_date,
)

logger = logging.getLogger(__name__)


def sync_imap_emails(user_id: int, *, limit: int = 50, days: int = 30) -> Dict[str, Any]:
    settings = get_user_imap_settings(user_id)
    if not settings:
        return {"success": False, "error": "IMAP not configured. Save Yahoo, iCloud, or IMAP settings first."}

    provider = infer_provider_from_imap_settings(settings)
    emails_synced = 0

    try:
        imap = connect_imap(settings)
    except Exception as exc:
        logger.error("IMAP connect failed user=%s: %s", user_id, exc)
        return {"success": False, "error": "Failed to connect to IMAP server"}

    try:
        since = (datetime.utcnow() - timedelta(days=max(1, days))).strftime("%d-%b-%Y")
        status, data = imap.uid("search", None, f"(SINCE {since})")
        if status != "OK":
            return {"success": False, "error": "IMAP search failed"}

        uids = data[0].split() if data and data[0] else []
        if limit > 0 and len(uids) > limit:
            uids = uids[-limit:]

        for uid in uids:
            uid_str = uid.decode() if isinstance(uid, bytes) else str(uid)
            try:
                existing = db_optimizer.execute_query(
                    """
                    SELECT id, attachments FROM synced_emails
                    WHERE user_id = ? AND external_id = ? AND provider = ?
                    """,
                    (user_id, uid_str, provider),
                )
                if existing:
                    from core.email_attachments import cache_attachments, synced_email_needs_attachment_backfill

                    row = existing[0]
                    if synced_email_needs_attachment_backfill(row.get("attachments")):
                        raw = fetch_imap_rfc822(imap, uid_str)
                        msg = email.message_from_bytes(raw)
                        attachments = extract_attachments_from_imap_message(msg)
                        if attachments:
                            cache_attachments(user_id, uid_str, attachments, provider=provider)
                    continue

                raw = fetch_imap_rfc822(imap, uid_str)
                msg = email.message_from_bytes(raw)
                subject = msg.get("Subject", "No Subject") or "No Subject"
                sender = msg.get("From", "Unknown") or "Unknown"
                received = parse_imap_message_date(msg)
                body = extract_body_from_imap_message(msg)
                labels = json.dumps(["UNREAD"])

                db_optimizer.execute_query(
                    """
                    INSERT INTO synced_emails
                    (user_id, external_id, provider, subject, sender, recipient, date, body, labels, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        user_id,
                        uid_str,
                        provider,
                        subject,
                        sender,
                        settings.get("username", ""),
                        received,
                        body,
                        labels,
                    ),
                    fetch=False,
                )
                emails_synced += 1

                attachments = extract_attachments_from_imap_message(msg)
                if attachments:
                    from core.email_attachments import cache_attachments

                    cache_attachments(user_id, uid_str, attachments, provider=provider)
            except Exception as msg_exc:
                logger.debug("IMAP message sync skipped uid=%s: %s", uid_str, msg_exc)
                continue
    finally:
        try:
            imap.logout()
        except Exception:
            pass

    label = {"yahoo": "Yahoo", "icloud": "Apple iCloud", "aol": "AOL"}.get(provider, "IMAP")
    return {
        "success": True,
        "count": emails_synced,
        "provider": provider,
        "message": f"{label} sync completed ({emails_synced} new messages)",
    }
