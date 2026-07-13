"""IMAP connection and attachment helpers for Yahoo, Apple iCloud, and generic IMAP inboxes."""

from __future__ import annotations

import email
import imaplib
import logging
from email.header import decode_header
from email.message import Message
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

IMAP_MAIL_PROVIDERS = frozenset({"imap", "yahoo", "icloud", "apple", "aol"})


def infer_provider_from_imap_settings(settings: Dict[str, Any]) -> str:
    server = (settings.get("imap_server") or "").lower()
    name = (settings.get("service_name") or "").lower()
    if "yahoo" in server or "yahoo" in name:
        return "yahoo"
    if "mail.me" in server or "icloud" in server or "icloud" in name or "apple" in name:
        return "icloud"
    if "aol" in server or "aol" in name:
        return "aol"
    return "imap"


def get_user_imap_settings(user_id: int) -> Optional[Dict[str, Any]]:
    from core.user_services import get_user_service_row

    row = get_user_service_row(user_id, "imap")
    if not row or not row.get("enabled"):
        return None
    settings = dict(row.get("settings") or {})
    if not settings.get("username") or not settings.get("password"):
        return None
    if not settings.get("imap_server"):
        return None
    return settings


def connect_imap(settings: Dict[str, Any]) -> imaplib.IMAP4:
    imap_server = settings["imap_server"]
    imap_port = int(settings.get("imap_port", 993))
    use_ssl = bool(settings.get("imap_ssl", settings.get("use_ssl", True)))
    if use_ssl:
        conn = imaplib.IMAP4_SSL(imap_server, imap_port)
    else:
        conn = imaplib.IMAP4(imap_server, imap_port)
    conn.login(settings["username"], settings["password"])
    conn.select("INBOX")
    return conn


def decode_mime_filename(raw: Optional[str]) -> str:
    if not raw:
        return "attachment"
    parts = decode_header(raw)
    decoded: List[str] = []
    for fragment, charset in parts:
        if isinstance(fragment, bytes):
            decoded.append(fragment.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(str(fragment))
    return "".join(decoded).strip() or "attachment"


def fetch_imap_rfc822(imap: imaplib.IMAP4, message_uid: str) -> bytes:
    """Fetch full message by IMAP UID (stable across sessions)."""
    status, data = imap.uid("fetch", str(message_uid), "(RFC822)")
    if status != "OK" or not data or not data[0]:
        raise RuntimeError(f"IMAP UID fetch failed for uid={message_uid}")
    chunk = data[0]
    if isinstance(chunk, tuple):
        return chunk[1]
    raise RuntimeError(f"IMAP UID fetch returned unexpected payload for uid={message_uid}")


def extract_body_from_imap_message(msg: Message) -> str:
    body_html = ""
    body_text = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            disposition = str(part.get("Content-Disposition") or "").lower()
            if "attachment" in disposition:
                continue
            mime = part.get_content_type()
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            if mime == "text/html" and not body_html:
                body_html = text
            elif mime == "text/plain" and not body_text:
                body_text = text
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body_text = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
    return body_html or body_text or ""


def extract_attachments_from_imap_message(msg: Message) -> List[Dict[str, Any]]:
    attachments: List[Dict[str, Any]] = []
    for idx, part in enumerate(msg.walk()):
        if part.get_content_maintype() == "multipart":
            continue
        disposition = str(part.get("Content-Disposition") or "")
        filename = part.get_filename()
        is_attachment = "attachment" in disposition.lower() or bool(filename)
        if not is_attachment:
            continue
        name = decode_mime_filename(filename) if filename else f"attachment-{idx}"
        payload = part.get_payload(decode=True) or b""
        attachments.append(
            {
                "attachment_id": f"part:{idx}",
                "filename": name,
                "mime_type": part.get_content_type(),
                "size": len(payload),
            }
        )
    return attachments


def get_imap_attachment_bytes(msg: Message, attachment_id: str) -> Optional[Tuple[bytes, str]]:
    part_key = attachment_id.replace("part:", "", 1) if attachment_id.startswith("part:") else attachment_id
    try:
        target_idx = int(part_key)
    except ValueError:
        return None
    for idx, part in enumerate(msg.walk()):
        if idx != target_idx:
            continue
        data = part.get_payload(decode=True) or b""
        return data, part.get_content_type()
    return None


def parse_imap_message_date(msg: Message) -> str:
    date_hdr = msg.get("Date")
    if not date_hdr:
        return ""
    try:
        return parsedate_to_datetime(date_hdr).isoformat()
    except Exception:
        return str(date_hdr)
