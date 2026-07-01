"""Flag-gated Postgres transcript persistence for the Fikiri site bot."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from company_chatbot import config
from company_chatbot.schemas import MessageResult
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"

_TABLES_READY = False


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json(payload: Any) -> str:
    return json.dumps(payload, default=str, separators=(",", ":"))


def _hash_client_value(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    salt = os.getenv("FIKIRI_SITE_BOT_TRANSCRIPT_HASH_SALT", "fikiri-site-chat").strip()
    digest = hashlib.sha256(f"{salt}:{raw}".encode("utf-8")).hexdigest()
    return digest[:64]


def ensure_site_chat_transcript_tables() -> None:
    global _TABLES_READY
    if _TABLES_READY:
        return

    db_optimizer.execute_query(
        """
        CREATE TABLE IF NOT EXISTS site_chat_sessions (
            id BIGSERIAL PRIMARY KEY,
            session_id TEXT NOT NULL UNIQUE,
            source_page TEXT,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            turn_count INTEGER NOT NULL DEFAULT 0,
            last_mode TEXT,
            latest_lead_tier TEXT,
            latest_lead_score INTEGER,
            latest_lead_synopsis TEXT,
            latest_handoff_path TEXT,
            hashed_ip TEXT,
            hashed_user_agent TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """,
        fetch=False,
    )
    db_optimizer.execute_query(
        """
        CREATE TABLE IF NOT EXISTS site_chat_messages (
            id BIGSERIAL PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            mode TEXT,
            grounded INTEGER,
            confidence REAL,
            sources_json TEXT,
            intake_json TEXT,
            handoff_json TEXT,
            lead_assessment_json TEXT,
            created_at TEXT NOT NULL
        )
        """,
        fetch=False,
    )
    db_optimizer.execute_query(
        """
        CREATE TABLE IF NOT EXISTS site_chat_transcript_reads (
            id BIGSERIAL PRIMARY KEY,
            session_id TEXT NOT NULL,
            reader_user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """,
        fetch=False,
    )
    db_optimizer.execute_query(
        """
        CREATE INDEX IF NOT EXISTS idx_site_chat_sessions_last_seen
        ON site_chat_sessions (last_seen_at DESC)
        """,
        fetch=False,
    )
    db_optimizer.execute_query(
        """
        CREATE INDEX IF NOT EXISTS idx_site_chat_messages_session_time
        ON site_chat_messages (session_id, created_at)
        """,
        fetch=False,
    )
    db_optimizer.execute_query(
        """
        CREATE INDEX IF NOT EXISTS idx_site_chat_transcript_reads_session
        ON site_chat_transcript_reads (session_id, created_at DESC)
        """,
        fetch=False,
    )
    _TABLES_READY = True


def is_persist_enabled() -> bool:
    return config.persist_transcripts_enabled()


def persist_message_turn(
    *,
    session_id: str,
    user_message: str,
    result: MessageResult,
    source_page: Optional[str] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Append user + assistant rows and upsert session summary. Never raises."""
    if not is_persist_enabled():
        return

    try:
        _persist_message_turn_impl(
            session_id=session_id,
            user_message=user_message,
            result=result,
            source_page=source_page,
            client_ip=client_ip,
            user_agent=user_agent,
        )
    except Exception as exc:
        logger.warning(
            "Site bot transcript persistence failed for session %s: %s",
            session_id,
            exc,
            exc_info=True,
        )


def _persist_message_turn_impl(
    *,
    session_id: str,
    user_message: str,
    result: MessageResult,
    source_page: Optional[str],
    client_ip: Optional[str],
    user_agent: Optional[str],
) -> None:
    ensure_site_chat_transcript_tables()
    now = _utcnow_iso()
    assessment = result.lead_assessment
    handoff_path = result.handoff.secondary or result.handoff.handoff_type or ""

    db_optimizer.execute_query(
        """
        INSERT INTO site_chat_sessions (
            session_id, source_page, first_seen_at, last_seen_at, turn_count, last_mode,
            latest_lead_tier, latest_lead_score, latest_lead_synopsis, latest_handoff_path,
            hashed_ip, hashed_user_agent, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            source_page = COALESCE(excluded.source_page, site_chat_sessions.source_page),
            last_seen_at = excluded.last_seen_at,
            turn_count = excluded.turn_count,
            last_mode = excluded.last_mode,
            latest_lead_tier = excluded.latest_lead_tier,
            latest_lead_score = excluded.latest_lead_score,
            latest_lead_synopsis = excluded.latest_lead_synopsis,
            latest_handoff_path = excluded.latest_handoff_path,
            hashed_ip = COALESCE(excluded.hashed_ip, site_chat_sessions.hashed_ip),
            hashed_user_agent = COALESCE(
                excluded.hashed_user_agent, site_chat_sessions.hashed_user_agent
            ),
            updated_at = excluded.updated_at
        """,
        (
            session_id,
            (source_page or "").strip() or None,
            now,
            now,
            result.turn_count,
            result.mode,
            assessment.tier,
            assessment.score,
            assessment.synopsis,
            handoff_path or None,
            _hash_client_value(client_ip or "") or None,
            _hash_client_value(user_agent or "") or None,
            now,
            now,
        ),
        fetch=False,
    )

    db_optimizer.execute_query(
        """
        INSERT INTO site_chat_messages (
            session_id, role, content, mode, grounded, confidence,
            sources_json, intake_json, handoff_json, lead_assessment_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            ROLE_USER,
            user_message,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            now,
        ),
        fetch=False,
    )

    db_optimizer.execute_query(
        """
        INSERT INTO site_chat_messages (
            session_id, role, content, mode, grounded, confidence,
            sources_json, intake_json, handoff_json, lead_assessment_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            ROLE_ASSISTANT,
            result.response,
            result.mode,
            1 if result.grounded else 0,
            result.confidence,
            _safe_json(result.sources) if result.sources else None,
            _safe_json(result.intake) if result.intake else None,
            _safe_json(result.handoff.to_dict()),
            _safe_json(assessment.to_dict()),
            now,
        ),
        fetch=False,
    )


def purge_expired_transcripts() -> int:
    """Delete sessions/messages older than retention window. Returns rows removed (approx)."""
    if not is_persist_enabled():
        return 0

    ensure_site_chat_transcript_tables()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=config.transcript_retention_days())).isoformat()

    old_sessions = db_optimizer.execute_query(
        "SELECT session_id FROM site_chat_sessions WHERE last_seen_at < ?",
        (cutoff,),
    )
    session_ids = [
        row["session_id"] if hasattr(row, "keys") else row[0] for row in (old_sessions or [])
    ]
    if not session_ids:
        return 0

    removed = 0
    for sid in session_ids:
        db_optimizer.execute_query(
            "DELETE FROM site_chat_messages WHERE session_id = ?",
            (sid,),
            fetch=False,
        )
        db_optimizer.execute_query(
            "DELETE FROM site_chat_transcript_reads WHERE session_id = ?",
            (sid,),
            fetch=False,
        )
        db_optimizer.execute_query(
            "DELETE FROM site_chat_sessions WHERE session_id = ?",
            (sid,),
            fetch=False,
        )
        removed += 1
    return removed


def record_transcript_audit(session_id: str, reader_user_id: str, action: str) -> None:
    ensure_site_chat_transcript_tables()
    db_optimizer.execute_query(
        """
        INSERT INTO site_chat_transcript_reads (session_id, reader_user_id, action, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (session_id, str(reader_user_id), action, _utcnow_iso()),
        fetch=False,
    )


def list_transcript_sessions(
    *,
    limit: int = 20,
    offset: int = 0,
    tier: Optional[str] = None,
    mode: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    ensure_site_chat_transcript_tables()
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    clauses = ["1=1"]
    params: List[Any] = []
    if tier:
        clauses.append("latest_lead_tier = ?")
        params.append(tier.strip().lower())
    if mode:
        clauses.append("last_mode = ?")
        params.append(mode.strip().lower())
    if date_from:
        clauses.append("last_seen_at >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("last_seen_at <= ?")
        params.append(date_to)

    where_sql = " AND ".join(clauses)
    count_rows = db_optimizer.execute_query(
        f"SELECT COUNT(*) AS total FROM site_chat_sessions WHERE {where_sql}",
        tuple(params),
    )
    total = 0
    if count_rows:
        row = count_rows[0]
        total = int(row["total"] if hasattr(row, "keys") else row[0])

    rows = db_optimizer.execute_query(
        f"""
        SELECT session_id, source_page, first_seen_at, last_seen_at, turn_count, last_mode,
               latest_lead_tier, latest_lead_score, latest_lead_synopsis, latest_handoff_path
        FROM site_chat_sessions
        WHERE {where_sql}
        ORDER BY last_seen_at DESC
        LIMIT ? OFFSET ?
        """,
        tuple(params + [limit, offset]),
    )
    sessions = [_session_summary_row(row) for row in (rows or [])]
    return {"sessions": sessions, "total": total, "limit": limit, "offset": offset}


def get_transcript_session(session_id: str) -> Optional[Dict[str, Any]]:
    ensure_site_chat_transcript_tables()
    rows = db_optimizer.execute_query(
        """
        SELECT session_id, source_page, first_seen_at, last_seen_at, turn_count, last_mode,
               latest_lead_tier, latest_lead_score, latest_lead_synopsis, latest_handoff_path,
               hashed_ip, hashed_user_agent, created_at, updated_at
        FROM site_chat_sessions
        WHERE session_id = ?
        LIMIT 1
        """,
        (session_id,),
    )
    if not rows:
        return None

    session_row = rows[0]
    messages = db_optimizer.execute_query(
        """
        SELECT role, content, mode, grounded, confidence, sources_json, intake_json,
               handoff_json, lead_assessment_json, created_at
        FROM site_chat_messages
        WHERE session_id = ?
        ORDER BY created_at ASC, id ASC
        """,
        (session_id,),
    )
    return {
        "session": _session_detail_row(session_row),
        "messages": [_message_row(row) for row in (messages or [])],
    }


def build_transcript_export(session_id: str, export_format: str = "text") -> Optional[Dict[str, Any]]:
    payload = get_transcript_session(session_id)
    if not payload:
        return None

    session = payload["session"]
    messages = payload["messages"]
    if export_format == "json":
        return {
            "format": "json",
            "session_id": session["session_id"],
            "created_at": session["first_seen_at"],
            "last_seen_at": session["last_seen_at"],
            "last_mode": session["last_mode"],
            "lead_assessment": {
                "tier": session["latest_lead_tier"],
                "score": session["latest_lead_score"],
                "synopsis": session["latest_lead_synopsis"],
            },
            "handoff_path": session["latest_handoff_path"],
            "messages": messages,
        }

    lines = [
        "Fikiri Site Chat Transcript",
        f"Session: {session['session_id']}",
        f"First seen: {session['first_seen_at']}",
        f"Last seen: {session['last_seen_at']}",
        f"Last mode: {session.get('last_mode') or 'n/a'}",
        (
            "Lead: "
            f"{session.get('latest_lead_tier') or 'n/a'} "
            f"(score {session.get('latest_lead_score', 0)})"
        ),
        f"Synopsis: {session.get('latest_lead_synopsis') or ''}",
        f"Handoff: {session.get('latest_handoff_path') or 'n/a'}",
        "---",
    ]
    for msg in messages:
        role = msg["role"].title()
        mode_suffix = f" / {msg['mode']}" if msg.get("mode") else ""
        lines.append(f"[{role}{mode_suffix}] {msg['content']}")
        if msg["role"] == ROLE_ASSISTANT:
            if msg.get("grounded") is not None:
                lines.append(f"  grounded: {bool(msg['grounded'])}, confidence: {msg.get('confidence')}")
            if msg.get("lead_assessment"):
                la = msg["lead_assessment"]
                lines.append(
                    f"  lead: {la.get('tier')} ({la.get('score')}) — {la.get('synopsis', '')}"
                )
            if msg.get("intake"):
                lines.append(f"  intake: {_safe_json(msg['intake'])}")
            if msg.get("handoff"):
                lines.append(f"  handoff: {_safe_json(msg['handoff'])}")
        lines.append("")

    return {
        "format": "text",
        "session_id": session["session_id"],
        "content": "\n".join(lines).strip() + "\n",
    }


def _session_summary_row(row: Any) -> Dict[str, Any]:
    def _get(key: str, idx: int):
        return row[key] if hasattr(row, "keys") else row[idx]

    return {
        "session_id": _get("session_id", 0),
        "source_page": _get("source_page", 1),
        "first_seen_at": _get("first_seen_at", 2),
        "last_seen_at": _get("last_seen_at", 3),
        "turn_count": _get("turn_count", 4),
        "last_mode": _get("last_mode", 5),
        "latest_lead_tier": _get("latest_lead_tier", 6),
        "latest_lead_score": _get("latest_lead_score", 7),
        "latest_lead_synopsis": _get("latest_lead_synopsis", 8),
        "latest_handoff_path": _get("latest_handoff_path", 9),
    }


def _session_detail_row(row: Any) -> Dict[str, Any]:
    summary = _session_summary_row(row)

    def _get(key: str, idx: int):
        return row[key] if hasattr(row, "keys") else row[idx]

    summary["hashed_ip"] = _get("hashed_ip", 10)
    summary["hashed_user_agent"] = _get("hashed_user_agent", 11)
    summary["created_at"] = _get("created_at", 12)
    summary["updated_at"] = _get("updated_at", 13)
    return summary


def _parse_json_field(raw: Any) -> Any:
    if raw is None or raw == "":
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None


def _message_row(row: Any) -> Dict[str, Any]:
    def _get(key: str, idx: int):
        return row[key] if hasattr(row, "keys") else row[idx]

    grounded_raw = _get("grounded", 3)
    return {
        "role": _get("role", 0),
        "content": _get("content", 1),
        "mode": _get("mode", 2),
        "grounded": bool(grounded_raw) if grounded_raw is not None else None,
        "confidence": _get("confidence", 4),
        "sources": _parse_json_field(_get("sources_json", 5)),
        "intake": _parse_json_field(_get("intake_json", 6)),
        "handoff": _parse_json_field(_get("handoff_json", 7)),
        "lead_assessment": _parse_json_field(_get("lead_assessment_json", 8)),
        "created_at": _get("created_at", 9),
    }


def clear_transcript_tables_for_tests() -> None:
    """Remove all site chat transcript rows (tests only)."""
    global _TABLES_READY
    ensure_site_chat_transcript_tables()
    for table in (
        "site_chat_transcript_reads",
        "site_chat_messages",
        "site_chat_sessions",
    ):
        db_optimizer.execute_query(f"DELETE FROM {table}", fetch=False)
    _TABLES_READY = True
