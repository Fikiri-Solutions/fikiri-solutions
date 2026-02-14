#!/usr/bin/env python3
"""
Centralized Redis Connection Helper
Handles Upstash Redis SSL certificate issues and provides consistent connection logic.
Supports REDIS_URL or Upstash env vars: UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN.
"""

import os
import logging
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Optional Redis integration
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


def _resolve_redis_url() -> Optional[str]:
    """Resolve Redis URL from REDIS_URL or from Upstash REST env vars."""
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return redis_url.strip()
    rest_url = os.getenv("UPSTASH_REDIS_REST_URL")
    rest_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if rest_url and rest_token:
        parsed = urlparse(rest_url.strip())
        host = parsed.hostname or parsed.netloc.split(":")[0]
        if host:
            return f"rediss://default:{rest_token.strip()}@{host}:6379"
    return None


def _is_test_mode() -> bool:
    return (
        os.getenv("FIKIRI_TEST_MODE") == "1"
        or os.getenv("FLASK_ENV") == "test"
        or bool(os.getenv("PYTEST_CURRENT_TEST"))
    )


def get_redis_client(decode_responses: bool = True, db: int = 0) -> Optional[redis.Redis]:
    """
    Get a Redis client with proper SSL handling for Upstash Redis
    
    Args:
        decode_responses: Whether to decode responses as strings
        db: Redis database number
    
    Returns:
        Redis client or None if connection fails
    """
    if not REDIS_AVAILABLE:
        return None

    if _is_test_mode():
        return None
    
    try:
        redis_url = _resolve_redis_url()

        if redis_url:
            # redis-py 5.x: SSL options must be in the URL query string, not kwargs
            if redis_url.startswith("rediss://"):
                sep = "&" if "?" in redis_url else "?"
                redis_url = f"{redis_url}{sep}ssl_cert_reqs=none"
            client = redis.from_url(
                redis_url,
                decode_responses=decode_responses,
                db=db,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            
            # Test connection
            client.ping()
            
            # Log success
            if redis_url.startswith('rediss://'):
                logger.info("✅ Redis connection established (Upstash TLS via from_url)")
            else:
                logger.info("✅ Redis connection established (standard via from_url)")
            
            return client
        else:
            # Try local Redis
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_password = os.getenv('REDIS_PASSWORD')
            
            client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                db=db,
                decode_responses=decode_responses,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            client.ping()
            logger.info(f"✅ Redis connection established (local): {redis_host}:{redis_port}")
            return client
            
    except redis.AuthenticationError as e:
        logger.error(f"❌ Redis authentication failed: {e}")
        logger.warning("⚠️ Check REDIS_URL or UPSTASH_REDIS_REST_* in .env")
        redis_url = _resolve_redis_url()
        if redis_url:
            parsed = urlparse(redis_url)
            logger.debug(f"   URL host: {parsed.hostname}, port: {parsed.port}")
            logger.debug(f"   Username: {parsed.username or 'default'}")
            logger.debug(f"   Password extracted: {'Yes' if parsed.password else 'No'}")
            logger.debug(f"   URL format: {'rediss:// (TLS)' if redis_url.startswith('rediss://') else 'redis:// (standard)'}")
        return None
    except redis.ConnectionError as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Redis connection error: {e}")
        return None


def is_redis_available() -> bool:
    """Check if Redis is available and working"""
    client = get_redis_client()
    if client:
        try:
            client.ping()
            return True
        except Exception as ping_error:
            logger.debug("Redis ping failed: %s", ping_error)
            return False
    return False
