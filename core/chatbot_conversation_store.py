"""
Durable chatbot conversation persistence (append-only, tenant-scoped).

Dev/local replay and analytics only — does not inject history into prompts.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from core.chatbot_retrieval import retrieval_metadata
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_SYSTEM = "system"
VALID_ROLES = frozenset({ROLE_USER, ROLE_ASSISTANT, ROLE_SYSTEM})


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_flag(name: str, *, default: bool) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def is_public_persistence_enabled() -> bool:
    """Public widget persists turns when true (default on)."""
    return _env_flag("FIKIRI_CHATBOT_CONVERSATION_PERSIST", default=True)


def is_preview_persistence_enabled() -> bool:
    """Dashboard preview persistence (default off)."""
    return _env_flag("FIKIRI_CHATBOT_PREVIEW_PERSIST", default=False)


def should_store_retrieval_debug(*, channel: str, debug_requested: bool = False) -> bool:
    """Internal/dev only: store retrieval_debug on assistant rows."""
    if not debug_requested:
        return False
    if channel != "preview":
        return False
    return _env_flag("FIKIRI_CHATBOT_STORE_RETRIEVAL_DEBUG", default=False)


def ensure_chatbot_conversation_tables() -> None:
    db_optimizer.execute_query(
        """
        CREATE TABLE IF NOT EXISTS chatbot_conversations (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            user_id TEXT,
            session_id TEXT,
            channel TEXT NOT NULL DEFAULT 'api',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_activity_at TEXT NOT NULL,
            UNIQUE(tenant_id, conversation_id)
        )
        """,
        fetch=False,
    )
    db_optimizer.execute_query(
        """
        CREATE TABLE IF NOT EXISTS chatbot_messages (
            id BIGSERIAL PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            retrieval_metadata_json TEXT,
            source_ids_json TEXT,
            fallback_used INTEGER NOT NULL DEFAULT 0,
            confidence REAL,
            correlation_id TEXT,
            retrieval_debug_json TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(tenant_id, conversation_id, message_id)
        )
        """,
        fetch=False,
    )
    db_optimizer.execute_query(
        """
        CREATE INDEX IF NOT EXISTS idx_chatbot_messages_tenant_conv_time
        ON chatbot_messages (tenant_id, conversation_id, created_at)
        """,
        fetch=False,
    )


def _normalize_tenant_id(tenant_id: Optional[str]) -> str:
    tid = str(tenant_id or "").strip()
    if not tid:
        raise ValueError("tenant_id is required for chatbot conversation persistence")
    return tid


def _normalize_conversation_id(conversation_id: Optional[str]) -> str:
    cid = str(conversation_id or "").strip()
    if not cid:
        raise ValueError("conversation_id is required")
    return cid


def get_or_create_conversation(
    *,
    tenant_id: str,
    conversation_id: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    channel: str = "api",
) -> None:
    """Upsert conversation header row (tenant-scoped)."""
    ensure_chatbot_conversation_tables()
    tid = _normalize_tenant_id(tenant_id)
    cid = _normalize_conversation_id(conversation_id)
    now = _utcnow_iso()
    uid = str(user_id) if user_id is not None else None
    sid = str(session_id).strip() if session_id else None
    ch = (channel or "api").strip() or "api"

    db_optimizer.execute_query(
        """
        INSERT INTO chatbot_conversations (
            tenant_id, conversation_id, user_id, session_id, channel,
            created_at, updated_at, last_activity_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(tenant_id, conversation_id) DO UPDATE SET
            user_id = COALESCE(excluded.user_id, chatbot_conversations.user_id),
            session_id = COALESCE(excluded.session_id, chatbot_conversations.session_id),
            channel = excluded.channel,
            updated_at = excluded.updated_at,
            last_activity_at = excluded.last_activity_at
        """,
        (tid, cid, uid, sid, ch, now, now, now),
        fetch=False,
    )


def append_message(
    *,
    tenant_id: str,
    conversation_id: str,
    role: str,
    content: str,
    message_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    channel: str = "api",
    retrieval_metadata: Optional[Dict[str, Any]] = None,
    source_ids: Optional[Sequence[str]] = None,
    fallback_used: bool = False,
    confidence: Optional[float] = None,
    correlation_id: Optional[str] = None,
    retrieval_debug: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Append one message (insert-only). Returns message_id used.
    Idempotent per (tenant_id, conversation_id, message_id).
    """
    ensure_chatbot_conversation_tables()
    role_key = str(role or "").strip().lower()
    if role_key not in VALID_ROLES:
        raise ValueError(f"invalid role: {role}")

    tid = _normalize_tenant_id(tenant_id)
    cid = _normalize_conversation_id(conversation_id)
    mid = str(message_id or "").strip() or str(uuid.uuid4())
    now = _utcnow_iso()

    get_or_create_conversation(
        tenant_id=tid,
        conversation_id=cid,
        user_id=user_id,
        session_id=session_id,
        channel=channel,
    )

    meta_json = (
        json.dumps(retrieval_metadata, sort_keys=True)[:20000]
        if retrieval_metadata
        else None
    )
    sources_json = (
        json.dumps(list(source_ids), sort_keys=True)[:10000]
        if source_ids
        else None
    )
    debug_json = (
        json.dumps(retrieval_debug, sort_keys=True)[:50000]
        if retrieval_debug
        else None
    )
    fb_int = 1 if fallback_used else 0

    db_optimizer.execute_query(
        """
        INSERT INTO chatbot_messages (
            tenant_id, conversation_id, message_id, role, content,
            retrieval_metadata_json, source_ids_json, fallback_used,
            confidence, correlation_id, retrieval_debug_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(tenant_id, conversation_id, message_id) DO NOTHING
        """,
        (
            tid,
            cid,
            mid,
            role_key,
            (content or "")[:100000],
            meta_json,
            sources_json,
            fb_int,
            confidence,
            correlation_id,
            debug_json,
            now,
        ),
        fetch=False,
    )

    db_optimizer.execute_query(
        """
        UPDATE chatbot_conversations
        SET updated_at = ?, last_activity_at = ?
        WHERE tenant_id = ? AND conversation_id = ?
        """,
        (now, now, tid, cid),
        fetch=False,
    )
    return mid


def list_conversation_messages(
    tenant_id: str,
    conversation_id: str,
    *,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """Replay messages in chronological order (tenant-isolated)."""
    ensure_chatbot_conversation_tables()
    tid = _normalize_tenant_id(tenant_id)
    cid = _normalize_conversation_id(conversation_id)
    cap = max(1, min(int(limit), 2000))

    rows = db_optimizer.execute_query(
        """
        SELECT message_id, role, content, retrieval_metadata_json, source_ids_json,
               fallback_used, confidence, correlation_id, retrieval_debug_json, created_at
        FROM chatbot_messages
        WHERE tenant_id = ? AND conversation_id = ?
        ORDER BY created_at ASC, id ASC
        LIMIT ?
        """,
        (tid, cid, cap),
    )
    out: List[Dict[str, Any]] = []
    for row in rows or []:
        item = dict(row)
        item["fallback_used"] = bool(int(row.get("fallback_used") or 0))
        for key in ("retrieval_metadata_json", "source_ids_json", "retrieval_debug_json"):
            raw = row.get(key)
            if raw:
                try:
                    item[key.replace("_json", "")] = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    item[key.replace("_json", "")] = None
        out.append(item)
    return out


def _compact_retrieval_metadata(
    retrieval_confidence: float,
    sources: Sequence[Dict[str, Any]],
    retrieval_debug: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    doc_ids, scores = retrieval_metadata(sources)
    meta: Dict[str, Any] = {
        "retrieval_confidence": round(float(retrieval_confidence or 0.0), 4),
        "source_count": len(sources or []),
        "retrieved_doc_ids": doc_ids,
        "retrieval_scores": scores,
    }
    if retrieval_debug:
        meta["final_source_count"] = retrieval_debug.get("final_source_count")
        meta["fallback_needed"] = retrieval_debug.get("fallback_needed")
    return meta


def persist_chatbot_turn(
    *,
    tenant_id: str,
    conversation_id: str,
    query: str,
    answer: str,
    assistant_message_id: str,
    sources: Sequence[Dict[str, Any]],
    fallback_used: bool,
    confidence: Optional[float],
    retrieval_confidence: float,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    channel: str = "api",
    correlation_id: Optional[str] = None,
    retrieval_debug: Optional[Dict[str, Any]] = None,
    store_retrieval_debug: bool = False,
) -> None:
    """
    Best-effort append of user + assistant messages for one turn.
    Never raises — logs and returns on failure.
    """
    try:
        doc_ids, _ = retrieval_metadata(sources)
        meta = _compact_retrieval_metadata(
            retrieval_confidence, sources, retrieval_debug=retrieval_debug
        )
        debug_payload = retrieval_debug if store_retrieval_debug else None

        user_mid = f"user-{assistant_message_id}"
        append_message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=ROLE_USER,
            content=query,
            message_id=user_mid,
            user_id=user_id,
            session_id=session_id,
            channel=channel,
            correlation_id=correlation_id,
        )
        append_message(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            role=ROLE_ASSISTANT,
            content=answer,
            message_id=assistant_message_id,
            user_id=user_id,
            session_id=session_id,
            channel=channel,
            retrieval_metadata=meta,
            source_ids=doc_ids,
            fallback_used=fallback_used,
            confidence=confidence,
            correlation_id=correlation_id,
            retrieval_debug=debug_payload,
        )
    except Exception as exc:
        logger.warning(
            "chatbot conversation persist skipped tenant=%s conv=%s: %s",
            tenant_id,
            conversation_id,
            exc,
            extra={
                "event": "chatbot.conversation.persist_failed",
                "service": "chatbot",
                "severity": "WARN",
            },
        )
