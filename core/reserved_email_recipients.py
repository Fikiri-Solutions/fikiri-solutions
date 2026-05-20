"""
Reserved / documentation email domains that must not receive real delivery.

IANA example.{com,net,org} publish Null MX (RFC 7505). RFC 2606 reserves *.test and
*.invalid. Gmail OAuth sends to these addresses produce DSN bounces in the connected
mailbox. Transactional SMTP jobs and Gmail paths share ``should_skip_real_email_delivery``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Exact domains (not only suffixes).
_RESERVED_IANA_EXAMPLE_DOMAINS = frozenset(
    {
        "example.com",
        "example.net",
        "example.org",
        "example.test",
        "example.invalid",
        "test.invalid",
    }
)

_LOCALHOST_DOMAINS = frozenset({"localhost", "localhost.localdomain"})


def recipient_domain(to_email: str) -> str:
    """Lowercase domain part of an address, or empty string."""
    if not to_email or "@" not in to_email:
        return ""
    return to_email.rsplit("@", 1)[-1].strip().lower()


def should_skip_real_email_delivery(to_email: str) -> bool:
    """
    True when the address must not be sent via SMTP or Gmail API.

    Invalid/empty addresses return False so existing validation can reject them.
    """
    domain = recipient_domain(to_email)
    if not domain:
        return False
    if domain in _RESERVED_IANA_EXAMPLE_DOMAINS:
        return True
    if domain in _LOCALHOST_DOMAINS:
        return True
    if domain.endswith(".test") or domain.endswith(".invalid"):
        return True
    return False


def log_skipped_gmail_delivery(
    *,
    user_id: Optional[int] = None,
    source: str,
    domain: str,
    reason: str = "reserved_recipient_domain",
) -> None:
    """Structured log without full recipient address (domain only)."""
    logger.info(
        "email.delivery.skipped_reserved_recipient",
        extra={
            "event": "email.delivery.skipped_reserved_recipient",
            "service": "email",
            "user_id": user_id,
            "source": source,
            "domain": domain,
            "reason": reason,
        },
    )


def gmail_skipped_send_result(*, channel: str = "gmail") -> Dict[str, Any]:
    """No-op success for Gmail client / callers expecting send result dict."""
    return {
        "success": True,
        "skipped": True,
        "reason": "reserved_recipient_domain",
        "channel": channel,
        "message_id": None,
        "thread_id": None,
    }
