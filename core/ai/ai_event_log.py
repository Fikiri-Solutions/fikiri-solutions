"""
Append-only AI lifecycle events (auditing / explainability). Inserts are best-effort.
Disable with FIKIRI_AI_EVENT_LOG=0 if needed.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from typing import Any, Dict, Optional

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

_MAX_PAYLOAD_BYTES = 16 * 1024

_AI_EVENT_LOG_ENABLED = os.getenv("FIKIRI_AI_EVENT_LOG", "1").lower() not in ("0", "false", "no")


def ai_event_logging_enabled() -> bool:
    return _AI_EVENT_LOG_ENABLED


def coerce_user_id(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def ensure_correlation_in_context(context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Ensure correlation_id exists. Mutates dict in place when context is not None; if None, uses a new dict.

    Matches LLMRouter rules: None or blank/whitespace-only strings get a new UUID; other values are str().strip().
    """
    ctx = context if context is not None else {}
    _cid = ctx.get("correlation_id")
    if _cid is None or (isinstance(_cid, str) and not _cid.strip()):
        ctx["correlation_id"] = str(uuid.uuid4())
    else:
        ctx["correlation_id"] = str(_cid).strip()
    return ctx


def text_summary(text: str, max_len: int = 200) -> str:
    t = (text or "").strip()
    if len(t) <= max_len:
        return t
    return t[:max_len] + "…"


def sha256_hex(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()


def record_ai_event(
    event_type: str,
    *,
    user_id: Optional[int] = None,
    entity_type: str = "ai",
    entity_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
    supersedes_event_id: Optional[int] = None,
    status: Optional[str] = None,
    error_message: Optional[str] = None,
    source: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    """
    Persist one AI event. Swallows all errors after logging. Returns new row id or None.
    """
    if not ai_event_logging_enabled():
        return None
    try:
        truncated = 0
        payload_json: Optional[str] = None
        if payload is not None:
            raw = json.dumps(payload, default=str, separators=(",", ":"))
            enc = raw.encode("utf-8")
            if len(enc) > _MAX_PAYLOAD_BYTES:
                enc = enc[:_MAX_PAYLOAD_BYTES]
                truncated = 1
                payload_json = enc.decode("utf-8", errors="ignore")
            else:
                payload_json = raw

        new_id = db_optimizer.execute_insert_returning_id(
            """
            INSERT INTO ai_events (
                user_id, event_type, entity_type, entity_id,
                correlation_id, supersedes_event_id,
                status, error_message, source,
                payload_json, payload_truncated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                event_type,
                entity_type,
                entity_id,
                correlation_id,
                supersedes_event_id,
                status,
                error_message,
                source,
                payload_json,
                truncated,
            ),
        )
        return new_id
    except Exception as exc:  # noqa: BLE001 — intentional best-effort sink
        logger.warning(
            "ai_events insert failed (non-fatal): %s",
            exc,
            extra={
                "event": "ai_event_insert_failed",
                "service": "ai",
                "severity": "WARN",
                "event_type": event_type,
                "correlation_id": correlation_id,
            },
        )
        return None


def build_router_envelope_base(
    *,
    correlation_id: str,
    router_trace_id: str,
    intent: str,
    source: str,
    context: Dict[str, Any],
    preprocessed_prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
) -> Dict[str, Any]:
    channel = {
        "source": source,
        "surface": str(context.get("surface") or "api"),
        "operation": str(context.get("operation") or context.get("channel") or ""),
    }
    return {
        "envelope_version": 1,
        "correlation_id": correlation_id,
        "router_trace_id": router_trace_id,
        "parent_event_id": context.get("ai_parent_event_id"),
        "channel": channel,
        "request": {
            "intent": intent,
            "input_summary": text_summary(preprocessed_prompt, 200),
            "input_sha256": sha256_hex(preprocessed_prompt),
            "prompt_template_id": context.get("prompt_template_id"),
            "schema_id": context.get("schema_id"),
        },
        "model": {
            "id": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        "tenant_id": context.get("tenant_id"),
        "conversation_id": context.get("conversation_id"),
        "approval": {"state": "none", "user_id": None, "decided_at": None, "reason": None},
        "execution": {
            "action_type": None,
            "linked_entity_type": context.get("ai_link_entity_type"),
            "linked_entity_id": coerce_user_id(context.get("ai_link_entity_id")),
            "external_ref": context.get("ai_external_ref"),
        },
    }


__all__ = [
    "ai_event_logging_enabled",
    "build_router_envelope_base",
    "coerce_user_id",
    "ensure_correlation_in_context",
    "record_ai_event",
    "sha256_hex",
    "text_summary",
]
