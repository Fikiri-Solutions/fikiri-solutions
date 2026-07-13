"""Backward-compatible re-exports — use core.email_attachments for new code."""

from core.email_attachments import (  # noqa: F401
    cache_attachments,
    extract_attachments_from_gmail_payload,
    extract_attachments_from_payload,
    fetch_gmail_attachments,
    list_cached_attachments,
    list_email_attachments,
    replace_email_attachments,
    update_synced_email_attachments_json,
)
