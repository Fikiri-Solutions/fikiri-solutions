"""
HTTP correlation_id for hybrid event architecture: stitch domain event tables without merging them.

Priority: X-Correlation-ID header > JSON body key (default correlation_id) > new UUID.
"""

from __future__ import annotations

import uuid
from typing import Any, Mapping, Optional, Union

try:
    from flask import Request
except ImportError:  # pragma: no cover
    Request = Any  # type: ignore[misc,assignment]


def get_or_create_correlation_id(
    request: Request,
    body: Optional[Mapping[str, Any]] = None,
    *,
    body_key: str = "correlation_id",
) -> str:
    """
    Return a non-empty correlation string for this request.
    Caller should pass the same value into CRM/email/AI/automation payloads and echo in responses.
    """
    if request is not None:
        hdr = request.headers.get("X-Correlation-ID")
        if hdr is not None and str(hdr).strip():
            return str(hdr).strip()
    if body is not None:
        raw = body.get(body_key)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return str(uuid.uuid4())
