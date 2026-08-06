"""Shared admin security state (Phase 1.6).

Canonical production backend: Redis via get_redis_client.
In-memory backend is development/test only.

Key namespace: fikiri:admin:*
Never stores passwords, MFA codes, JWTs, cookies, or OAuth credentials.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

KEY_PREFIX = "fikiri:admin:"


def _env_flag(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def is_production() -> bool:
    return (os.getenv("FLASK_ENV") or "").strip().lower() == "production"


def is_test_or_dev() -> bool:
    env = (os.getenv("FLASK_ENV") or "").strip().lower()
    return (
        os.getenv("FIKIRI_TEST_MODE") == "1"
        or env in ("test", "development", "dev", "")
        or bool(os.getenv("PYTEST_CURRENT_TEST"))
        or not is_production()
    )


def configured_store_backend() -> str:
    raw = (os.getenv("ADMIN_SECURITY_STORE") or "").strip().lower()
    if raw in ("redis", "memory"):
        return raw
    return "redis" if is_production() else "memory"


class AdminSecurityStoreUnavailable(RuntimeError):
    """Shared store required but unavailable — privileged ops must fail closed."""


class _MemoryBackend:
    """Process-local store for tests and local development only."""

    def __init__(self) -> None:
        self._data: Dict[str, tuple] = {}  # key -> (value, exp_or_None)
        self._sets: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()

    def _purge(self, key: str) -> None:
        item = self._data.get(key)
        if item and item[1] is not None and item[1] <= time.time():
            self._data.pop(key, None)

    def set_json(self, key: str, value: Any, ttl: int) -> None:
        with self._lock:
            self._data[key] = (json.dumps(value), time.time() + max(1, int(ttl)))

    def get_json(self, key: str) -> Optional[Any]:
        with self._lock:
            self._purge(key)
            item = self._data.get(key)
            if not item:
                return None
            try:
                return json.loads(item[0])
            except Exception:
                return None

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)
            self._sets.pop(key, None)

    def sadd(self, key: str, member: str) -> None:
        with self._lock:
            self._sets.setdefault(key, set()).add(member)

    def smembers(self, key: str) -> List[str]:
        with self._lock:
            return list(self._sets.get(key, set()))

    def srem(self, key: str, member: str) -> None:
        with self._lock:
            s = self._sets.get(key)
            if s:
                s.discard(member)
                if not s:
                    self._sets.pop(key, None)

    def incr(self, key: str, ttl: int) -> int:
        with self._lock:
            self._purge(key)
            item = self._data.get(key)
            count = 0
            if item:
                try:
                    count = int(json.loads(item[0]))
                except Exception:
                    count = 0
            count += 1
            exp = item[1] if item and item[1] else time.time() + max(1, int(ttl))
            if not item:
                exp = time.time() + max(1, int(ttl))
            self._data[key] = (json.dumps(count), exp)
            return count

    def set_nx(self, key: str, value: Any, ttl: int) -> bool:
        with self._lock:
            self._purge(key)
            if key in self._data:
                return False
            self._data[key] = (json.dumps(value), time.time() + max(1, int(ttl)))
            return True

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._sets.clear()


class _RedisBackend:
    def __init__(self, client: Any) -> None:
        self.client = client

    def set_json(self, key: str, value: Any, ttl: int) -> None:
        self.client.setex(key, max(1, int(ttl)), json.dumps(value))

    def get_json(self, key: str) -> Optional[Any]:
        raw = self.client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    def delete(self, key: str) -> None:
        self.client.delete(key)

    def sadd(self, key: str, member: str) -> None:
        self.client.sadd(key, member)

    def smembers(self, key: str) -> List[str]:
        members = self.client.smembers(key) or set()
        return [m.decode() if isinstance(m, bytes) else str(m) for m in members]

    def srem(self, key: str, member: str) -> None:
        self.client.srem(key, member)

    def incr(self, key: str, ttl: int) -> int:
        pipe = self.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, max(1, int(ttl)))
        results = pipe.execute()
        return int(results[0])

    def set_nx(self, key: str, value: Any, ttl: int) -> bool:
        return bool(self.client.set(key, json.dumps(value), nx=True, ex=max(1, int(ttl))))


# Shared memory singleton so multi-app tests share state.
_MEMORY_SINGLETON = _MemoryBackend()
_STORE: Optional["AdminSecurityStore"] = None
_STORE_LOCK = threading.Lock()


class AdminSecurityStore:
    """Facade over Redis or memory backends for privileged admin state."""

    def __init__(self, backend: Any, *, mode: str) -> None:
        self._backend = backend
        self.mode = mode
        self.available = backend is not None

    @property
    def is_shared(self) -> bool:
        return self.mode == "redis" and self.available

    def require_available(self) -> None:
        if not self.available:
            raise AdminSecurityStoreUnavailable("admin security store unavailable")

    def k(self, *parts: str) -> str:
        return KEY_PREFIX + ":".join(str(p) for p in parts)

    def set_json(self, key: str, value: Any, ttl: int) -> None:
        self.require_available()
        self._backend.set_json(key, value, ttl)

    def get_json(self, key: str) -> Optional[Any]:
        self.require_available()
        return self._backend.get_json(key)

    def delete(self, key: str) -> None:
        self.require_available()
        self._backend.delete(key)

    def sadd(self, key: str, member: str) -> None:
        self.require_available()
        self._backend.sadd(key, member)

    def smembers(self, key: str) -> List[str]:
        self.require_available()
        return self._backend.smembers(key)

    def srem(self, key: str, member: str) -> None:
        self.require_available()
        self._backend.srem(key, member)

    def incr(self, key: str, ttl: int) -> int:
        self.require_available()
        return self._backend.incr(key, ttl)

    def set_nx(self, key: str, value: Any, ttl: int) -> bool:
        self.require_available()
        return self._backend.set_nx(key, value, ttl)


def _connect_redis_backend() -> Optional[_RedisBackend]:
    try:
        from core.redis_connection_helper import get_redis_client

        client = get_redis_client(decode_responses=True, db=int(os.getenv("REDIS_DB", 0)))
        if client is None:
            return None
        client.ping()
        return _RedisBackend(client)
    except Exception as exc:
        logger.warning("Admin security Redis unavailable: %s", exc)
        return None


def get_admin_security_store(*, force_reload: bool = False) -> AdminSecurityStore:
    global _STORE
    with _STORE_LOCK:
        if _STORE is not None and not force_reload:
            return _STORE

        mode = configured_store_backend()
        if mode == "memory":
            if is_production() and not _env_flag("ADMIN_SECURITY_ALLOW_MEMORY_IN_PRODUCTION", False):
                logger.error("ADMIN_SECURITY_STORE=memory rejected in production")
                _STORE = AdminSecurityStore(None, mode="memory")
                return _STORE
            _STORE = AdminSecurityStore(_MEMORY_SINGLETON, mode="memory")
            return _STORE

        # redis mode
        backend = _connect_redis_backend()
        if backend is None:
            if is_test_or_dev() and not is_production():
                logger.warning("Admin security store falling back to memory (non-production)")
                _STORE = AdminSecurityStore(_MEMORY_SINGLETON, mode="memory")
            else:
                _STORE = AdminSecurityStore(None, mode="redis")
            return _STORE
        _STORE = AdminSecurityStore(backend, mode="redis")
        return _STORE


def reset_admin_security_store_for_tests() -> None:
    global _STORE
    with _STORE_LOCK:
        _MEMORY_SINGLETON.clear()
        _STORE = None


def clear_admin_security_store_for_tests() -> None:
    store = get_admin_security_store()
    if store.mode == "memory" and isinstance(store._backend, _MemoryBackend):
        store._backend.clear()
    reset_admin_security_store_for_tests()
    # Re-init memory for subsequent tests
    os.environ.setdefault("ADMIN_SECURITY_STORE", "memory")
    get_admin_security_store(force_reload=True)
