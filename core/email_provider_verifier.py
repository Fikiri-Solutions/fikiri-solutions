"""
Email provider / legitimacy heuristics for onboarding.

Goal: reduce fake accounts without being overly strict.
We use DNS MX lookup as a lightweight signal that a domain can receive email.
"""

from __future__ import annotations

import json
import time
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import dns.resolver  # type: ignore
except Exception:  # pragma: no cover
    dns = None

# When import succeeds, `dns` is bound by `import dns.resolver`. Do not reference
# undefined names here — a prior bug checked `dns_resolver is None` even though
# that variable only existed in the except branch, causing NameError on signup.


_in_memory_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL_SECONDS = int(10 * 60)  # 10 minutes


def _normalize_domain(domain: str) -> Optional[str]:
    domain = (domain or "").strip().lower()
    if not domain:
        return None
    # Remove trailing dot for FQDNs like "gmail.com."
    if domain.endswith("."):
        domain = domain[:-1]
    # Minimal sanity checks.
    if " " in domain or "/" in domain:
        return None
    if "@" in domain:
        # Caller should pass domain only, but be defensive.
        domain = domain.split("@", 1)[-1]
    return domain or None


def _get_cached(domain: str) -> Optional[Dict[str, Any]]:
    now = time.time()
    cached = _in_memory_cache.get(domain)
    if not cached:
        return None
    ts, value = cached
    if now - ts > _CACHE_TTL_SECONDS:
        _in_memory_cache.pop(domain, None)
        return None
    return value


def _set_cached(domain: str, value: Dict[str, Any]) -> None:
    _in_memory_cache[domain] = (time.time(), value)

    # Best-effort Redis cache (optional dependency / optional availability).
    try:
        from core.redis_cache import get_cache

        cache = get_cache()
        if cache and getattr(cache, "is_connected", None) and cache.is_connected():
            # Use deterministic key, keep payload small.
            key = f"fikiri:email:mx:{domain}"
            cache.redis_client.setex(key, _CACHE_TTL_SECONDS, json.dumps(value))
    except Exception as e:  # pragma: no cover
        logger.debug("Redis cache for mx verification failed: %s", e)


def _get_cached_from_redis(domain: str) -> Optional[Dict[str, Any]]:
    try:
        from core.redis_cache import get_cache

        cache = get_cache()
        if not cache or not getattr(cache, "is_connected", None) or not cache.is_connected():
            return None
        key = f"fikiri:email:mx:{domain}"
        cached = cache.redis_client.get(key)
        if not cached:
            return None
        return json.loads(cached)
    except Exception:  # pragma: no cover
        return None


def check_email_domain_has_mx(
    domain: str,
    timeout_seconds: float = 2.0,
) -> Dict[str, Any]:
    """
    Returns:
      {
        "domain": "<normalized>",
        "has_mx": true|false|null,
        "mx_records": <int>,
        "reason": "OK" | "NO_MX" | "INVALID_DOMAIN" | "DNS_ERROR" | "UNKNOWN",
      }

    - has_mx == null means we couldn't determine (e.g., DNS library missing, resolver errors).
    """
    normalized = _normalize_domain(domain)
    if not normalized:
        return {
            "domain": domain,
            "has_mx": None,
            "mx_records": 0,
            "reason": "INVALID_DOMAIN",
        }

    redis_cached = _get_cached_from_redis(normalized)
    if redis_cached is not None:
        return redis_cached

    cached = _get_cached(normalized)
    if cached is not None:
        return cached

    # Degrade gracefully if dnspython isn't available.
    if dns is None:
        result = {
            "domain": normalized,
            "has_mx": None,
            "mx_records": 0,
            "reason": "DNS_LIBRARY_UNAVAILABLE",
        }
        _set_cached(normalized, result)
        return result

    try:
        resolver = dns.resolver.Resolver()  # type: ignore[attr-defined]
        resolver.timeout = timeout_seconds
        resolver.lifetime = timeout_seconds
        answers = resolver.resolve(normalized, "MX")

        mx_records = 0
        for _ in answers:
            mx_records += 1

        has_mx = mx_records > 0
        result = {
            "domain": normalized,
            "has_mx": has_mx,
            "mx_records": mx_records,
            "reason": "OK" if has_mx else "NO_MX",
        }
        _set_cached(normalized, result)
        return result
    except Exception as e:
        # Many failure modes exist: NXDOMAIN, NoAnswer, timeouts, etc.
        # We treat them as "unknown" (soft behavior).
        result = {
            "domain": normalized,
            "has_mx": None,
            "mx_records": 0,
            "reason": f"DNS_ERROR: {type(e).__name__}",
        }
        _set_cached(normalized, result)
        return result

