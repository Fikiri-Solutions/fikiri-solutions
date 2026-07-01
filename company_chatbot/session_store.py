"""Redis-backed session storage for the Fikiri site bot (in-memory fallback in test/dev)."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Optional, Protocol, TYPE_CHECKING

from company_chatbot import config
from company_chatbot.intake import IntakeSlots

if TYPE_CHECKING:
    from company_chatbot.orchestrator import SessionState

logger = logging.getLogger(__name__)

_SESSION_KEY_PREFIX = "fikiri:site_chat:session:"

_memory_lock = threading.Lock()
_memory_sessions: Dict[str, str] = {}


class SessionStoreBackend(Protocol):
    def save(self, session_id: str, payload: str, ttl_seconds: int) -> None: ...

    def load(self, session_id: str) -> Optional[str]: ...

    def delete(self, session_id: str) -> None: ...

    def clear_all(self) -> None: ...


class MemorySessionBackend:
    def save(self, session_id: str, payload: str, ttl_seconds: int) -> None:
        _ = ttl_seconds
        with _memory_lock:
            _memory_sessions[session_id] = payload

    def load(self, session_id: str) -> Optional[str]:
        with _memory_lock:
            return _memory_sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        with _memory_lock:
            _memory_sessions.pop(session_id, None)

    def clear_all(self) -> None:
        with _memory_lock:
            _memory_sessions.clear()


class RedisSessionBackend:
    def __init__(self, client) -> None:
        self._client = client

    def _key(self, session_id: str) -> str:
        return f"{_SESSION_KEY_PREFIX}{session_id}"

    def save(self, session_id: str, payload: str, ttl_seconds: int) -> None:
        self._client.setex(self._key(session_id), ttl_seconds, payload)

    def load(self, session_id: str) -> Optional[str]:
        value = self._client.get(self._key(session_id))
        return value if value else None

    def delete(self, session_id: str) -> None:
        self._client.delete(self._key(session_id))

    def clear_all(self) -> None:
        cursor = 0
        pattern = f"{_SESSION_KEY_PREFIX}*"
        while True:
            cursor, keys = self._client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                self._client.delete(*keys)
            if cursor == 0:
                break


_backend: Optional[SessionStoreBackend] = None
_backend_lock = threading.Lock()


def _serialize_state(state: "SessionState") -> str:
    payload = {
        "session_id": state.session_id,
        "turn_count": state.turn_count,
        "last_mode": state.last_mode,
        "created_at": state.created_at.isoformat(),
        "intake_active": state.intake_active,
        "intake_mode": state.intake_mode,
        "intake_slots": state.intake_slots.to_dict(),
        "response_history": list(state.response_history),
        "last_user_message": state.last_user_message,
    }
    return json.dumps(payload)


def _deserialize_state(raw: str) -> Optional["SessionState"]:
    from company_chatbot.orchestrator import SessionState

    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None

    slots_data = data.get("intake_slots") or {}
    slots = IntakeSlots()
    for key in (
        "industry",
        "main_pain",
        "timeline",
        "contact_email",
        "name",
        "business_name",
        "email_declined",
    ):
        if key in slots_data:
            setattr(slots, key, slots_data[key])

    created_raw = data.get("created_at")
    try:
        created_at = datetime.fromisoformat(created_raw) if created_raw else datetime.now(timezone.utc)
    except (TypeError, ValueError):
        created_at = datetime.now(timezone.utc)

    return SessionState(
        session_id=data.get("session_id", ""),
        turn_count=int(data.get("turn_count") or 0),
        last_mode=data.get("last_mode") or config.MODE_FALLBACK,
        created_at=created_at,
        intake_active=bool(data.get("intake_active")),
        intake_mode=data.get("intake_mode") or config.MODE_EXPLORE_FIT,
        intake_slots=slots,
        response_history=list(data.get("response_history") or []),
        last_user_message=data.get("last_user_message") or "",
    )


def _resolve_backend() -> SessionStoreBackend:
    global _backend
    with _backend_lock:
        if _backend is not None:
            return _backend

        if config.is_test_mode():
            _backend = MemorySessionBackend()
            return _backend

        try:
            from core.redis_connection_helper import get_redis_client

            client = get_redis_client(decode_responses=True)
            if client is not None:
                _backend = RedisSessionBackend(client)
                return _backend
        except Exception as exc:
            logger.warning("Site bot Redis session store unavailable: %s", exc)

        logger.warning("Site bot using in-memory session store (Redis unavailable)")
        _backend = MemorySessionBackend()
        return _backend


def reset_session_store_backend_for_tests() -> None:
    """Force in-memory backend (tests only)."""
    global _backend
    with _backend_lock:
        _backend = MemorySessionBackend()
        _backend.clear_all()


def save_session(state: "SessionState") -> None:
    backend = _resolve_backend()
    ttl = config.session_ttl_seconds()
    backend.save(state.session_id, _serialize_state(state), ttl)


def load_session(session_id: str) -> Optional[SessionState]:
    if not session_id:
        return None
    backend = _resolve_backend()
    raw = backend.load(session_id)
    if not raw:
        return None
    return _deserialize_state(raw)


def delete_session(session_id: str) -> None:
    _resolve_backend().delete(session_id)


def clear_sessions_for_tests() -> None:
    reset_session_store_backend_for_tests()
