"""
Append-only chatbot / FAQ / knowledge-base content events and durable current-state rows.

Events are immutable; updates and deletes append new rows. Current-state tables serve live content.
Skipped during pytest (PYTEST_CURRENT_TEST) to avoid polluting shared dev DBs.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

_MAX_PAYLOAD_BYTES = 48 * 1024

EVENT_FAQ_CREATED = "faq.created"
EVENT_FAQ_UPDATED = "faq.updated"
EVENT_FAQ_DELETED = "faq.deleted"
EVENT_KB_DOC_CREATED = "kb.document.created"
EVENT_KB_DOC_UPDATED = "kb.document.updated"
EVENT_KB_DOC_DELETED = "kb.document.deleted"
EVENT_CHATBOT_CONFIG_UPDATED = "chatbot.config.updated"
EVENT_CHATBOT_RESPONSE_GENERATED = "chatbot.response_generated"
EVENT_CHATBOT_RESPONSE_CORRECTED = "chatbot.response_corrected"

ENTITY_FAQ = "faq"
ENTITY_KB_DOCUMENT = "kb_document"
ENTITY_CHATBOT_CONFIG = "chatbot_config"
ENTITY_CHATBOT_TURN = "chatbot_turn"


def _skip_side_effects() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


def persistence_enabled() -> bool:
    if _skip_side_effects():
        return False
    try:
        return bool(db_optimizer.table_exists("chatbot_content_events"))
    except Exception:
        return False


def hydration_enabled() -> bool:
    if _skip_side_effects():
        return False
    try:
        return bool(db_optimizer.table_exists("chatbot_faq_current"))
    except Exception:
        return False


def kb_hydration_enabled() -> bool:
    if _skip_side_effects():
        return False
    try:
        return bool(db_optimizer.table_exists("chatbot_kb_current"))
    except Exception:
        return False


def _serialize_payload(payload: Optional[Dict[str, Any]]) -> Tuple[Optional[str], int]:
    if payload is None:
        return None, 0
    raw = json.dumps(payload, default=str, separators=(",", ":"))
    enc = raw.encode("utf-8")
    if len(enc) > _MAX_PAYLOAD_BYTES:
        enc = enc[:_MAX_PAYLOAD_BYTES]
        return enc.decode("utf-8", errors="ignore"), 1
    return raw, 0


def content_fingerprint_from_sources(sources: Optional[List[Dict[str, Any]]]) -> str:
    """Stable short fingerprint of retrieval sources for linking responses to KB/FAQ state."""
    if not sources:
        return ""
    parts = []
    for s in sources:
        sid = s.get("id")
        parts.append(f"{s.get('type', '')}:{sid}")
    h = hashlib.sha256("|".join(parts).encode("utf-8", errors="replace")).hexdigest()
    return h[:40]


def _insert_event_tx(
    cursor,
    *,
    user_id: Optional[int],
    source: Optional[str],
    event_type: str,
    entity_type: str,
    entity_id: str,
    correlation_id: Optional[str],
    supersedes_event_id: Optional[int],
    payload: Optional[Dict[str, Any]],
    status: str = "applied",
    error_message: Optional[str] = None,
) -> Optional[int]:
    """
    Insert one event row inside the caller's transaction and return its id.

    Uses ``INSERT ... RETURNING id`` so it works on both Postgres (where
    ``cursor.lastrowid`` is always ``None``) and SQLite >= 3.35.
    """
    payload_json, truncated = _serialize_payload(payload)
    cursor.execute(
        """
        INSERT INTO chatbot_content_events (
            user_id, source, event_type, entity_type, entity_id,
            correlation_id, supersedes_event_id, payload_json, payload_truncated,
            status, error_message, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        (
            user_id,
            source,
            event_type,
            entity_type,
            entity_id,
            correlation_id,
            supersedes_event_id,
            payload_json,
            truncated,
            status,
            error_message,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    # PG (RealDictCursor) returns a dict; SQLite (Row factory) is also dict-like.
    return int(row["id"]) if "id" in row else int(row[0])


def record_chatbot_response_generated(
    *,
    message_id: str,
    conversation_id: str,
    user_id: Optional[int],
    correlation_id: Optional[str],
    query_excerpt: str,
    response_excerpt: str,
    sources: Optional[List[Dict[str, Any]]],
    content_fingerprint: str,
    llm_trace_id: Optional[str],
    confidence: Optional[float],
    fallback_used: bool,
    source: str = "public_chatbot",
) -> None:
    if not persistence_enabled():
        return
    payload = {
        "snapshot_after": {
            "message_id": message_id,
            "conversation_id": conversation_id,
            "query_excerpt": (query_excerpt or "")[:8000],
            "response_excerpt": (response_excerpt or "")[:8000],
            "content_fingerprint": content_fingerprint,
            "llm_trace_id": llm_trace_id,
            "confidence": confidence,
            "fallback_used": fallback_used,
            "sources_preview": (sources or [])[:12],
        }
    }
    try:
        with db_optimizer.transaction() as (conn, cur):
            _insert_event_tx(
                cur,
                user_id=user_id,
                source=source,
                event_type=EVENT_CHATBOT_RESPONSE_GENERATED,
                entity_type=ENTITY_CHATBOT_TURN,
                entity_id=message_id,
                correlation_id=correlation_id,
                supersedes_event_id=None,
                payload=payload,
            )
            conn.commit()
    except Exception as exc:
        logger.warning("chatbot.response_generated event failed (non-fatal): %s", exc)


def record_chatbot_response_corrected(
    *,
    user_id: Optional[int],
    correlation_id: Optional[str],
    message_id: Optional[str],
    question: str,
    original_answer: str,
    corrected_answer: str,
    rating: Optional[str],
    source: str = "chatbot_feedback",
) -> None:
    if not persistence_enabled():
        return
    payload = {
        "snapshot_after": {
            "question": (question or "")[:8000],
            "original_answer": (original_answer or "")[:8000],
            "corrected_answer": (corrected_answer or "")[:8000],
            "rating": rating,
            "message_id": message_id,
        }
    }
    eid = message_id or question[:80]
    try:
        with db_optimizer.transaction() as (conn, cur):
            _insert_event_tx(
                cur,
                user_id=user_id,
                source=source,
                event_type=EVENT_CHATBOT_RESPONSE_CORRECTED,
                entity_type=ENTITY_CHATBOT_TURN,
                entity_id=eid[:500],
                correlation_id=correlation_id,
                supersedes_event_id=None,
                payload=payload,
            )
            conn.commit()
    except Exception as exc:
        logger.warning("chatbot.response_corrected event failed (non-fatal): %s", exc)


def get_faq_vector_key(faq_id: str) -> Optional[str]:
    try:
        if not db_optimizer.table_exists("chatbot_faq_current"):
            return None
        rows = db_optimizer.execute_query(
            "SELECT vector_key FROM chatbot_faq_current WHERE faq_id = ?",
            (faq_id,),
            fetch=True,
        )
        if not rows:
            return None
        row = rows[0]
        r = dict(row) if not isinstance(row, dict) else row
        vk = r.get("vector_key")
        return str(vk) if vk is not None else None
    except Exception:
        return None


def set_faq_vector_key(faq_id: str, vector_key: str) -> None:
    if not persistence_enabled() or not vector_key:
        return
    try:
        db_optimizer.execute_query(
            """
            UPDATE chatbot_faq_current SET vector_key = ?, updated_at = ?
            WHERE faq_id = ?
            """,
            (str(vector_key), datetime.now(timezone.utc).isoformat(), faq_id),
            fetch=False,
        )
    except Exception as exc:
        logger.warning("set_faq_vector_key failed (non-fatal): %s", exc)


def persist_faq_created(
    *,
    faq_id: str,
    user_id: Optional[int],
    source: str,
    correlation_id: Optional[str],
    snapshot_after: Dict[str, Any],
    vector_key: Optional[str] = None,
) -> None:
    if not persistence_enabled():
        return
    now = datetime.now(timezone.utc).isoformat()
    payload = {"snapshot_after": snapshot_after, "vector": {"key": vector_key}}
    try:
        with db_optimizer.transaction() as (conn, cur):
            eid = _insert_event_tx(
                cur,
                user_id=user_id,
                source=source,
                event_type=EVENT_FAQ_CREATED,
                entity_type=ENTITY_FAQ,
                entity_id=faq_id,
                correlation_id=correlation_id,
                supersedes_event_id=None,
                payload=payload,
            )
            cur.execute(
                """
                INSERT INTO chatbot_faq_current (
                    faq_id, user_id, question, answer, category, keywords_json,
                    variations_json, priority, content_version, last_event_id, vector_key,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                ON CONFLICT(faq_id) DO UPDATE SET
                    user_id = excluded.user_id,
                    question = excluded.question,
                    answer = excluded.answer,
                    category = excluded.category,
                    keywords_json = excluded.keywords_json,
                    variations_json = excluded.variations_json,
                    priority = excluded.priority,
                    content_version = chatbot_faq_current.content_version + 1,
                    last_event_id = excluded.last_event_id,
                    vector_key = COALESCE(excluded.vector_key, chatbot_faq_current.vector_key),
                    updated_at = excluded.updated_at
                """,
                (
                    faq_id,
                    user_id,
                    snapshot_after["question"],
                    snapshot_after["answer"],
                    snapshot_after["category"],
                    json.dumps(snapshot_after.get("keywords") or []),
                    json.dumps(snapshot_after.get("variations") or []),
                    int(snapshot_after.get("priority") or 1),
                    eid,
                    vector_key,
                    now,
                    now,
                ),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("persist_faq_created failed (non-fatal): %s", exc)


def persist_faq_updated(
    *,
    faq_id: str,
    user_id: Optional[int],
    source: str,
    correlation_id: Optional[str],
    snapshot_before: Dict[str, Any],
    snapshot_after: Dict[str, Any],
    vector_key: Optional[str] = None,
) -> None:
    if not persistence_enabled():
        return
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "snapshot_before": snapshot_before,
        "snapshot_after": snapshot_after,
        "vector": {"key": vector_key},
    }
    try:
        with db_optimizer.transaction() as (conn, cur):
            eid = _insert_event_tx(
                cur,
                user_id=user_id,
                source=source,
                event_type=EVENT_FAQ_UPDATED,
                entity_type=ENTITY_FAQ,
                entity_id=faq_id,
                correlation_id=correlation_id,
                supersedes_event_id=None,
                payload=payload,
            )
            cur.execute(
                """
                INSERT INTO chatbot_faq_current (
                    faq_id, user_id, question, answer, category, keywords_json,
                    variations_json, priority, content_version, last_event_id, vector_key,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                ON CONFLICT(faq_id) DO UPDATE SET
                    user_id = excluded.user_id,
                    question = excluded.question,
                    answer = excluded.answer,
                    category = excluded.category,
                    keywords_json = excluded.keywords_json,
                    variations_json = excluded.variations_json,
                    priority = excluded.priority,
                    content_version = chatbot_faq_current.content_version + 1,
                    last_event_id = excluded.last_event_id,
                    vector_key = COALESCE(excluded.vector_key, chatbot_faq_current.vector_key),
                    updated_at = excluded.updated_at
                """,
                (
                    faq_id,
                    user_id,
                    snapshot_after["question"],
                    snapshot_after["answer"],
                    snapshot_after["category"],
                    json.dumps(snapshot_after.get("keywords") or []),
                    json.dumps(snapshot_after.get("variations") or []),
                    int(snapshot_after.get("priority") or 1),
                    eid,
                    vector_key,
                    now,
                    now,
                ),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("persist_faq_updated failed (non-fatal): %s", exc)


def persist_faq_deleted(
    *,
    faq_id: str,
    user_id: Optional[int],
    source: str,
    correlation_id: Optional[str],
    snapshot_before: Dict[str, Any],
) -> None:
    if not persistence_enabled():
        return
    payload = {"snapshot_before": snapshot_before}
    try:
        with db_optimizer.transaction() as (conn, cur):
            _insert_event_tx(
                cur,
                user_id=user_id,
                source=source,
                event_type=EVENT_FAQ_DELETED,
                entity_type=ENTITY_FAQ,
                entity_id=faq_id,
                correlation_id=correlation_id,
                supersedes_event_id=None,
                payload=payload,
            )
            cur.execute("DELETE FROM chatbot_faq_current WHERE faq_id = ?", (faq_id,))
            conn.commit()
    except Exception as exc:
        logger.warning("persist_faq_deleted failed (non-fatal): %s", exc)


def persist_kb_document_created(
    *,
    doc_id: str,
    tenant_id: Optional[str],
    user_id: Optional[int],
    source: str,
    correlation_id: Optional[str],
    snapshot_after: Dict[str, Any],
) -> None:
    if not persistence_enabled():
        return
    now = datetime.now(timezone.utc).isoformat()
    vid = (snapshot_after.get("metadata") or {}).get("vector_id")
    payload = {"snapshot_after": snapshot_after, "vector": {"key": vid}}
    try:
        with db_optimizer.transaction() as (conn, cur):
            eid = _insert_event_tx(
                cur,
                user_id=user_id,
                source=source,
                event_type=EVENT_KB_DOC_CREATED,
                entity_type=ENTITY_KB_DOCUMENT,
                entity_id=doc_id,
                correlation_id=correlation_id,
                supersedes_event_id=None,
                payload=payload,
            )
            cur.execute(
                """
                INSERT INTO chatbot_kb_current (
                    doc_id, user_id, tenant_id, title, content, summary,
                    document_type, format, category, tags_json, keywords_json, author,
                    metadata_json, content_version, last_event_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    user_id = excluded.user_id,
                    tenant_id = excluded.tenant_id,
                    title = excluded.title,
                    content = excluded.content,
                    summary = excluded.summary,
                    document_type = excluded.document_type,
                    format = excluded.format,
                    category = excluded.category,
                    tags_json = excluded.tags_json,
                    keywords_json = excluded.keywords_json,
                    author = excluded.author,
                    metadata_json = excluded.metadata_json,
                    content_version = chatbot_kb_current.content_version + 1,
                    last_event_id = excluded.last_event_id,
                    updated_at = excluded.updated_at
                """,
                (
                    doc_id,
                    user_id,
                    tenant_id,
                    snapshot_after["title"],
                    snapshot_after["content"],
                    snapshot_after.get("summary") or "",
                    snapshot_after["document_type"],
                    snapshot_after.get("format") or "markdown",
                    snapshot_after.get("category") or "general",
                    json.dumps(snapshot_after.get("tags") or []),
                    json.dumps(snapshot_after.get("keywords") or []),
                    snapshot_after.get("author") or "",
                    json.dumps(snapshot_after.get("metadata") or {}),
                    eid,
                    now,
                    now,
                ),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("persist_kb_document_created failed (non-fatal): %s", exc)


def persist_kb_document_updated(
    *,
    doc_id: str,
    tenant_id: Optional[str],
    user_id: Optional[int],
    source: str,
    correlation_id: Optional[str],
    snapshot_before: Dict[str, Any],
    snapshot_after: Dict[str, Any],
) -> None:
    if not persistence_enabled():
        return
    now = datetime.now(timezone.utc).isoformat()
    vid = (snapshot_after.get("metadata") or {}).get("vector_id")
    payload = {
        "snapshot_before": snapshot_before,
        "snapshot_after": snapshot_after,
        "vector": {"key": vid},
    }
    try:
        with db_optimizer.transaction() as (conn, cur):
            eid = _insert_event_tx(
                cur,
                user_id=user_id,
                source=source,
                event_type=EVENT_KB_DOC_UPDATED,
                entity_type=ENTITY_KB_DOCUMENT,
                entity_id=doc_id,
                correlation_id=correlation_id,
                supersedes_event_id=None,
                payload=payload,
            )
            cur.execute(
                """
                INSERT INTO chatbot_kb_current (
                    doc_id, user_id, tenant_id, title, content, summary,
                    document_type, format, category, tags_json, keywords_json, author,
                    metadata_json, content_version, last_event_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    user_id = excluded.user_id,
                    tenant_id = excluded.tenant_id,
                    title = excluded.title,
                    content = excluded.content,
                    summary = excluded.summary,
                    document_type = excluded.document_type,
                    format = excluded.format,
                    category = excluded.category,
                    tags_json = excluded.tags_json,
                    keywords_json = excluded.keywords_json,
                    author = excluded.author,
                    metadata_json = excluded.metadata_json,
                    content_version = chatbot_kb_current.content_version + 1,
                    last_event_id = excluded.last_event_id,
                    updated_at = excluded.updated_at
                """,
                (
                    doc_id,
                    user_id,
                    tenant_id,
                    snapshot_after["title"],
                    snapshot_after["content"],
                    snapshot_after.get("summary") or "",
                    snapshot_after["document_type"],
                    snapshot_after.get("format") or "markdown",
                    snapshot_after.get("category") or "general",
                    json.dumps(snapshot_after.get("tags") or []),
                    json.dumps(snapshot_after.get("keywords") or []),
                    snapshot_after.get("author") or "",
                    json.dumps(snapshot_after.get("metadata") or {}),
                    eid,
                    now,
                    now,
                ),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("persist_kb_document_updated failed (non-fatal): %s", exc)


def persist_kb_document_deleted(
    *,
    doc_id: str,
    user_id: Optional[int],
    source: str,
    correlation_id: Optional[str],
    snapshot_before: Dict[str, Any],
) -> None:
    if not persistence_enabled():
        return
    payload = {"snapshot_before": snapshot_before}
    try:
        with db_optimizer.transaction() as (conn, cur):
            _insert_event_tx(
                cur,
                user_id=user_id,
                source=source,
                event_type=EVENT_KB_DOC_DELETED,
                entity_type=ENTITY_KB_DOCUMENT,
                entity_id=doc_id,
                correlation_id=correlation_id,
                supersedes_event_id=None,
                payload=payload,
            )
            cur.execute("DELETE FROM chatbot_kb_current WHERE doc_id = ?", (doc_id,))
            conn.commit()
    except Exception as exc:
        logger.warning("persist_kb_document_deleted failed (non-fatal): %s", exc)


def load_persisted_faqs() -> List[Dict[str, Any]]:
    if not hydration_enabled():
        return []
    try:
        rows = db_optimizer.execute_query(
            """
            SELECT faq_id, user_id, question, answer, category, keywords_json,
                   variations_json, priority, content_version, vector_key
            FROM chatbot_faq_current
            ORDER BY updated_at ASC
            """,
            fetch=True,
        )
        if not rows:
            return []
        out = []
        for row in rows:
            r = dict(row) if not isinstance(row, dict) else row
            out.append(
                {
                    "faq_id": r["faq_id"],
                    "user_id": r.get("user_id"),
                    "question": r["question"],
                    "answer": r["answer"],
                    "category": r["category"],
                    "keywords": json.loads(r["keywords_json"] or "[]"),
                    "variations": json.loads(r["variations_json"] or "[]"),
                    "priority": r.get("priority") or 1,
                    "content_version": r.get("content_version") or 1,
                    "vector_key": r.get("vector_key"),
                }
            )
        return out
    except Exception as exc:
        logger.warning("load_persisted_faqs failed: %s", exc)
        return []


def load_persisted_kb_rows() -> List[Dict[str, Any]]:
    if not kb_hydration_enabled():
        return []
    try:
        rows = db_optimizer.execute_query(
            """
            SELECT doc_id, user_id, tenant_id, title, content, summary,
                   document_type, format, category, tags_json, keywords_json, author,
                   metadata_json, content_version
            FROM chatbot_kb_current
            ORDER BY updated_at ASC
            """,
            fetch=True,
        )
        if not rows:
            return []
        out = []
        for row in rows:
            r = dict(row) if not isinstance(row, dict) else row
            meta = json.loads(r["metadata_json"] or "{}")
            out.append(
                {
                    "doc_id": r["doc_id"],
                    "user_id": r.get("user_id"),
                    "tenant_id": r.get("tenant_id"),
                    "title": r["title"],
                    "content": r["content"],
                    "summary": r.get("summary") or "",
                    "document_type": r["document_type"],
                    "format": r.get("format") or "markdown",
                    "category": r.get("category") or "general",
                    "tags": json.loads(r["tags_json"] or "[]"),
                    "keywords": json.loads(r["keywords_json"] or "[]"),
                    "author": r.get("author") or "",
                    "metadata": meta,
                    "content_version": r.get("content_version") or 1,
                }
            )
        return out
    except Exception as exc:
        logger.warning("load_persisted_kb_rows failed: %s", exc)
        return []


def record_chatbot_config_updated(
    *,
    user_id: Optional[int],
    source: str,
    correlation_id: Optional[str],
    config_key: str,
    snapshot_before: Optional[Dict[str, Any]],
    snapshot_after: Dict[str, Any],
) -> None:
    if not persistence_enabled():
        return
    payload: Dict[str, Any] = {"snapshot_after": snapshot_after}
    if snapshot_before is not None:
        payload["snapshot_before"] = snapshot_before
    try:
        with db_optimizer.transaction() as (conn, cur):
            _insert_event_tx(
                cur,
                user_id=user_id,
                source=source,
                event_type=EVENT_CHATBOT_CONFIG_UPDATED,
                entity_type=ENTITY_CHATBOT_CONFIG,
                entity_id=config_key[:500],
                correlation_id=correlation_id,
                supersedes_event_id=None,
                payload=payload,
            )
            conn.commit()
    except Exception as exc:
        logger.warning("chatbot.config.updated event failed (non-fatal): %s", exc)


__all__ = [
    "content_fingerprint_from_sources",
    "hydration_enabled",
    "kb_hydration_enabled",
    "load_persisted_faqs",
    "load_persisted_kb_rows",
    "persistence_enabled",
    "persist_faq_created",
    "persist_faq_deleted",
    "persist_faq_updated",
    "persist_kb_document_created",
    "persist_kb_document_deleted",
    "persist_kb_document_updated",
    "record_chatbot_config_updated",
    "record_chatbot_response_corrected",
    "record_chatbot_response_generated",
    "get_faq_vector_key",
    "set_faq_vector_key",
    "EVENT_FAQ_CREATED",
    "EVENT_FAQ_DELETED",
    "EVENT_FAQ_UPDATED",
    "EVENT_KB_DOC_CREATED",
    "EVENT_KB_DOC_DELETED",
    "EVENT_KB_DOC_UPDATED",
    "ENTITY_FAQ",
    "ENTITY_KB_DOCUMENT",
]
