"""Email attachment extraction, cache, and provider-aware fetch for the inbox."""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
from typing import Any, Dict, List, Optional

import requests

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

_SKIP_ATTACHMENT_MIME_PREFIXES = ("text/plain", "text/html", "multipart/")

OUTLOOK_PROVIDER_ALIASES = frozenset(
    {"outlook", "microsoft", "microsoft365", "office365", "msgraph"}
)
IMAP_PROVIDER_ALIASES = frozenset({"imap", "yahoo", "icloud", "apple", "aol"})


def normalize_mail_provider(provider: Optional[str]) -> str:
    """Map provider aliases to canonical inbox provider slug."""
    slug = (provider or "gmail").strip().lower()
    if slug in OUTLOOK_PROVIDER_ALIASES:
        return "outlook"
    if slug == "apple":
        return "icloud"
    if slug in IMAP_PROVIDER_ALIASES:
        return slug
    return slug or "gmail"


def resolve_email_provider(user_id: int, email_id: str) -> str:
    """Return synced_emails provider for this message id, default gmail."""
    try:
        rows = db_optimizer.execute_query(
            """
            SELECT provider FROM synced_emails
            WHERE user_id = ? AND (external_id = ? OR gmail_id = ?)
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id, email_id, email_id),
        )
        if rows:
            provider = normalize_mail_provider(rows[0].get("provider") or "gmail")
            return provider
    except Exception as exc:
        logger.debug("resolve_email_provider failed: %s", exc)
    return "gmail"


def extract_attachments_from_gmail_payload(payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Walk a Gmail message payload and return attachment metadata."""
    found: Dict[str, Dict[str, Any]] = {}

    def walk(part: Dict[str, Any]) -> None:
        if not isinstance(part, dict):
            return
        body = part.get("body") or {}
        attachment_id = (body.get("attachmentId") or "").strip()
        if attachment_id:
            mime_type = (part.get("mimeType") or "application/octet-stream").strip()
            filename = (part.get("filename") or "").strip()
            if not filename:
                if mime_type.startswith(_SKIP_ATTACHMENT_MIME_PREFIXES):
                    pass
                else:
                    ext = mimetypes.guess_extension(mime_type.split(";")[0].strip()) or ""
                    filename = f"attachment-{attachment_id[:8]}{ext}"
            if filename:
                found[attachment_id] = {
                    "attachment_id": attachment_id,
                    "filename": filename,
                    "mime_type": mime_type,
                    "size": int(body.get("size") or 0),
                }
        for sub in part.get("parts") or []:
            if isinstance(sub, dict):
                walk(sub)

    if isinstance(payload, dict):
        walk(payload)
    return list(found.values())


def extract_attachments_from_outlook_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize Microsoft Graph attachment list."""
    attachments: List[Dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        att_id = (item.get("id") or "").strip()
        if not att_id:
            continue
        odata_type = (item.get("@odata.type") or "").lower()
        if "referenceattachment" in odata_type:
            continue
        filename = (item.get("name") or "").strip()
        if not filename:
            filename = f"attachment-{att_id[:8]}"
        attachments.append(
            {
                "attachment_id": att_id,
                "filename": filename,
                "mime_type": (item.get("contentType") or "application/octet-stream").strip(),
                "size": int(item.get("size") or 0),
            }
        )
    return attachments


def replace_email_attachments(user_id: int, email_id: str, attachments: List[Dict[str, Any]]) -> None:
    """Replace cached attachment rows for a message."""
    db_optimizer.execute_query(
        "DELETE FROM email_attachments WHERE user_id = ? AND email_id = ?",
        (user_id, email_id),
        fetch=False,
    )
    for att in attachments:
        db_optimizer.execute_query(
            """
            INSERT INTO email_attachments (
                user_id, email_id, attachment_id, filename, mime_type, size, stored_path
            ) VALUES (?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                user_id,
                email_id,
                att["attachment_id"],
                att["filename"],
                att.get("mime_type"),
                int(att.get("size") or 0),
            ),
            fetch=False,
        )


def update_synced_email_attachments_json(
    user_id: int,
    email_id: str,
    attachments: List[Dict[str, Any]],
    *,
    provider: str,
) -> None:
    """Store attachment metadata on synced_emails for list badges."""
    try:
        db_optimizer.execute_query(
            """
            UPDATE synced_emails
            SET attachments = ?
            WHERE user_id = ? AND provider = ?
              AND (external_id = ? OR gmail_id = ?)
            """,
            (json.dumps(attachments), user_id, provider, email_id, email_id),
            fetch=False,
        )
    except Exception as exc:
        logger.debug("synced_emails attachments update skipped: %s", exc)


def cache_attachments(
    user_id: int,
    email_id: str,
    attachments: List[Dict[str, Any]],
    *,
    provider: str,
) -> None:
    if not attachments:
        return
    replace_email_attachments(user_id, email_id, attachments)
    update_synced_email_attachments_json(user_id, email_id, attachments, provider=provider)


def synced_email_needs_attachment_backfill(raw_attachments: Any) -> bool:
    """True when synced_emails.attachments is empty or missing."""
    if not raw_attachments or raw_attachments in ("[]", "null", ""):
        return True
    try:
        parsed = json.loads(raw_attachments) if isinstance(raw_attachments, str) else raw_attachments
        return not parsed
    except (json.JSONDecodeError, TypeError):
        return True


def list_cached_attachments(user_id: int, email_id: str) -> List[Dict[str, Any]]:
    rows = db_optimizer.execute_query(
        """
        SELECT id, attachment_id, filename, mime_type, size, created_at
        FROM email_attachments
        WHERE user_id = ? AND email_id = ?
        ORDER BY filename
        """,
        (user_id, email_id),
    )
    return [dict(row) for row in rows] if rows else []


def fetch_gmail_attachments(user_id: int, email_id: str, *, cache: bool = True) -> List[Dict[str, Any]]:
    from integrations.gmail.gmail_client import gmail_client

    service = gmail_client.get_gmail_service_for_user(user_id)
    message = (
        service.users()
        .messages()
        .get(userId="me", id=email_id, format="full")
        .execute()
    )
    attachments = extract_attachments_from_gmail_payload(message.get("payload"))
    if cache:
        cache_attachments(user_id, email_id, attachments, provider="gmail")
    return attachments


def fetch_outlook_attachments(user_id: int, email_id: str, *, cache: bool = True) -> List[Dict[str, Any]]:
    from integrations.outlook.outlook_sync import get_valid_outlook_token

    access_token = get_valid_outlook_token(user_id)
    if not access_token:
        raise RuntimeError("No valid Outlook token")

    url = f"https://graph.microsoft.com/v1.0/me/messages/{email_id}/attachments"
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    response.raise_for_status()
    attachments = extract_attachments_from_outlook_items(response.json().get("value") or [])
    if cache:
        cache_attachments(user_id, email_id, attachments, provider="outlook")
    return attachments


def fetch_imap_attachments(
    user_id: int,
    email_id: str,
    provider: str,
    *,
    cache: bool = True,
) -> List[Dict[str, Any]]:
    import email

    from core.imap_mail_helpers import (
        connect_imap,
        extract_attachments_from_imap_message,
        fetch_imap_rfc822,
        get_user_imap_settings,
        infer_provider_from_imap_settings,
    )

    settings = get_user_imap_settings(user_id)
    if not settings:
        raise RuntimeError("IMAP not configured")

    resolved_provider = normalize_mail_provider(provider or infer_provider_from_imap_settings(settings))
    imap = connect_imap(settings)
    try:
        raw = fetch_imap_rfc822(imap, email_id)
        msg = email.message_from_bytes(raw)
        attachments = extract_attachments_from_imap_message(msg)
    finally:
        try:
            imap.logout()
        except Exception:
            pass

    if cache and attachments:
        cache_attachments(user_id, email_id, attachments, provider=resolved_provider)
    return attachments


def fetch_attachments_for_provider(
    user_id: int,
    email_id: str,
    provider: str,
    *,
    cache: bool = True,
) -> List[Dict[str, Any]]:
    normalized = normalize_mail_provider(provider)
    if normalized == "outlook":
        return fetch_outlook_attachments(user_id, email_id, cache=cache)
    if normalized in IMAP_PROVIDER_ALIASES:
        return fetch_imap_attachments(user_id, email_id, normalized, cache=cache)
    return fetch_gmail_attachments(user_id, email_id, cache=cache)


def list_email_attachments(user_id: int, email_id: str) -> List[Dict[str, Any]]:
    """Cached rows first; live provider fetch when cache is empty."""
    cached = list_cached_attachments(user_id, email_id)
    if cached:
        return cached
    provider = resolve_email_provider(user_id, email_id)
    try:
        live = fetch_attachments_for_provider(user_id, email_id, provider, cache=True)
        if not live:
            return []
        return list_cached_attachments(user_id, email_id)
    except Exception as exc:
        logger.warning(
            "%s attachment list failed user=%s email=%s: %s",
            provider,
            user_id,
            email_id,
            exc,
        )
        return []


def download_attachment_bytes(
    user_id: int,
    email_id: str,
    attachment_id: str,
    *,
    provider: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Download attachment bytes from Gmail, Outlook, or IMAP (Yahoo/iCloud/etc.)."""
    resolved = normalize_mail_provider(provider or resolve_email_provider(user_id, email_id))
    if resolved == "outlook":
        from integrations.outlook.outlook_sync import get_valid_outlook_token

        access_token = get_valid_outlook_token(user_id)
        if not access_token:
            return None
        url = (
            f"https://graph.microsoft.com/v1.0/me/messages/{email_id}"
            f"/attachments/{attachment_id}/$value"
        )
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=60,
        )
        response.raise_for_status()
        data = response.content
        return {"data": data, "size": len(data)}

    if resolved in IMAP_PROVIDER_ALIASES:
        import email

        from core.imap_mail_helpers import (
            connect_imap,
            fetch_imap_rfc822,
            get_imap_attachment_bytes,
            get_user_imap_settings,
        )

        settings = get_user_imap_settings(user_id)
        if not settings:
            return None
        imap = connect_imap(settings)
        try:
            raw = fetch_imap_rfc822(imap, email_id)
            msg = email.message_from_bytes(raw)
            part = get_imap_attachment_bytes(msg, attachment_id)
            if not part:
                return None
            data, mime_type = part
            return {"data": data, "size": len(data), "mime_type": mime_type}
        finally:
            try:
                imap.logout()
            except Exception:
                pass

    from integrations.gmail.gmail_client import gmail_client

    return gmail_client.get_attachment(user_id, email_id, attachment_id)


# Backward-compatible alias used by Gmail sync
extract_attachments_from_payload = extract_attachments_from_gmail_payload
