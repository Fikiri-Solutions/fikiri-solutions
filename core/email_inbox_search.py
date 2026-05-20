"""Helpers for inbox list search (Gmail q= and synced_emails SQL)."""

from __future__ import annotations

from typing import Any, Optional


def sanitize_inbox_search_query(raw: Any) -> Optional[str]:
    """Normalize user search text for Gmail q= and SQL LIKE (bounded, single-line)."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    text = text.replace("\r", " ").replace("\n", " ")
    return text[:200]


def gmail_inbox_list_query(filter_type: str, search: Optional[str] = None) -> str:
    """Build Gmail messages.list q= for inbox tab + optional user search."""
    if filter_type == "unread":
        base = "in:inbox is:unread"
    elif filter_type == "read":
        base = "in:inbox is:read"
    else:
        base = "in:inbox"
    term = sanitize_inbox_search_query(search)
    if not term:
        return base
    return f"{base} {term}"


def synced_inbox_search_sql_and_params(
    search: Optional[str],
) -> tuple[str, tuple]:
    """SQL fragment + params for synced_emails text search."""
    term = sanitize_inbox_search_query(search)
    if not term:
        return "", ()
    like = f"%{term}%"
    return (
        " AND (subject LIKE ? OR sender LIKE ? OR recipient LIKE ? OR COALESCE(body, '') LIKE ?)",
        (like, like, like, like),
    )
