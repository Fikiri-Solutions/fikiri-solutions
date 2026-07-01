"""Token-bucket rate limiting scoped to /api/site/chat/* routes."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from company_chatbot import config

logger = logging.getLogger(__name__)

_RATE_KEY_PREFIX = "fikiri:site_chat:ratelimit:"

_memory_lock = threading.Lock()
_memory_buckets: Dict[str, Tuple[float, float]] = {}


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int = 0


def _bucket_key(route: str, scope: str, identifier: str) -> str:
    safe_id = (identifier or "unknown").strip()[:128]
    return f"{_RATE_KEY_PREFIX}{route}:{scope}:{safe_id}"


def _token_bucket_take_memory(key: str, now: float) -> RateLimitResult:
    capacity = float(config.rate_limit_burst())
    refill_per_second = config.rate_limit_per_minute() / 60.0

    with _memory_lock:
        tokens, last_ts = _memory_buckets.get(key, (capacity, now))
        elapsed = max(0.0, now - last_ts)
        tokens = min(capacity, tokens + elapsed * refill_per_second)
        if tokens < 1.0:
            deficit = 1.0 - tokens
            retry = max(1, int(deficit / refill_per_second) if refill_per_second > 0 else 60)
            _memory_buckets[key] = (tokens, now)
            return RateLimitResult(allowed=False, retry_after_seconds=retry)

        tokens -= 1.0
        _memory_buckets[key] = (tokens, now)
        return RateLimitResult(allowed=True)


def _token_bucket_take_redis(key: str, client, now: float) -> RateLimitResult:
    capacity = float(config.rate_limit_burst())
    refill_per_second = config.rate_limit_per_minute() / 60.0
    ttl = max(120, int(capacity / refill_per_second) + 1) if refill_per_second > 0 else 120

    try:
        pipe = client.pipeline()
        pipe.get(key)
        pipe.get(f"{key}:ts")
        stored_tokens, stored_ts = pipe.execute()
    except Exception as exc:
        logger.warning("Site bot rate limit Redis read failed, allowing request: %s", exc)
        return RateLimitResult(allowed=True)

    if stored_tokens is None or stored_ts is None:
        tokens = capacity - 1.0
        try:
            pipe = client.pipeline()
            pipe.setex(key, ttl, str(tokens))
            pipe.setex(f"{key}:ts", ttl, str(now))
            pipe.execute()
        except Exception as exc:
            logger.warning("Site bot rate limit Redis write failed, allowing request: %s", exc)
        return RateLimitResult(allowed=True)

    try:
        tokens = float(stored_tokens)
        last_ts = float(stored_ts)
    except (TypeError, ValueError):
        tokens = capacity
        last_ts = now

    elapsed = max(0.0, now - last_ts)
    tokens = min(capacity, tokens + elapsed * refill_per_second)
    if tokens < 1.0:
        deficit = 1.0 - tokens
        retry = max(1, int(deficit / refill_per_second) if refill_per_second > 0 else 60)
        try:
            pipe = client.pipeline()
            pipe.setex(key, ttl, str(tokens))
            pipe.setex(f"{key}:ts", ttl, str(now))
            pipe.execute()
        except Exception as exc:
            logger.warning("Site bot rate limit Redis write failed: %s", exc)
        return RateLimitResult(allowed=False, retry_after_seconds=retry)

    tokens -= 1.0
    try:
        pipe = client.pipeline()
        pipe.setex(key, ttl, str(tokens))
        pipe.setex(f"{key}:ts", ttl, str(now))
        pipe.execute()
    except Exception as exc:
        logger.warning("Site bot rate limit Redis write failed: %s", exc)
    return RateLimitResult(allowed=True)


def _take_token(route: str, scope: str, identifier: str) -> RateLimitResult:
    key = _bucket_key(route, scope, identifier)
    now = time.time()

    if config.is_test_mode():
        return _token_bucket_take_memory(key, now)

    try:
        from core.redis_connection_helper import get_redis_client

        client = get_redis_client(decode_responses=True)
        if client is None:
            return _token_bucket_take_memory(key, now)
        return _token_bucket_take_redis(key, client, now)
    except Exception as exc:
        logger.warning("Site bot rate limit backend error, using memory fallback: %s", exc)
        return _token_bucket_take_memory(key, now)


def check_session_start_limits(client_ip: str) -> RateLimitResult:
    return _take_token("session_start", "ip", client_ip)


def check_message_limits(client_ip: str, session_id: str) -> RateLimitResult:
    ip_result = _take_token("message", "ip", client_ip)
    if not ip_result.allowed:
        return ip_result
    return _take_token("message", "session", session_id)


def clear_rate_limits_for_tests() -> None:
    with _memory_lock:
        _memory_buckets.clear()
