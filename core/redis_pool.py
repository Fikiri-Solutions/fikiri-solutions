#!/usr/bin/env python3
"""
Shared Redis Connection Pool for Fikiri Solutions
Prevents "max clients reached" errors by centralizing Redis connections
Supports Upstash Redis with TLS/SSL
"""

import os
import logging
from typing import Optional

# Optional Redis integration
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None

def get_redis_client(decode_responses: bool = True) -> Optional[redis.Redis]:
    """
    Get shared Redis client instance with Upstash TLS/SSL support
    
    Args:
        decode_responses: Whether to decode responses as strings (default: True)
    
    Returns:
        Redis client instance or None if unavailable
    """
    global _redis_client
    
    if not REDIS_AVAILABLE:
        if os.getenv('FLASK_ENV') != 'production':
            logger.debug("Redis not available, using in-memory fallback")
        return None
    
    if os.getenv('DISABLE_REDIS', 'false').lower() == 'true':
        logger.info("Redis usage disabled via DISABLE_REDIS flag")
        return None
    
    # Return existing client if available and connected
    if _redis_client is not None:
        try:
            _redis_client.ping()
            return _redis_client
        except Exception:
            # Connection lost, reset and reconnect
            _redis_client = None
    
    try:
        try:
            from core.redis_connection_helper import _resolve_redis_url
            redis_url = _resolve_redis_url() or os.getenv('REDIS_URL')
        except Exception:
            redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            logger.warning("REDIS_URL not set, Redis features will be unavailable")
            return None
        
        # Check if this is an Upstash Redis URL (rediss:// or https://)
        is_upstash = redis_url.startswith('rediss://') or redis_url.startswith('https://')
        allow_insecure_tls = os.getenv('ALLOW_INSECURE_REDIS_TLS', 'false').lower() == 'true'
        
        # For Upstash with TLS, handle SSL certificate verification
        if is_upstash:
            import ssl
            from urllib.parse import urlparse
            
            # Parse the Redis URL
            parsed = urlparse(redis_url)
            
            # Ensure we're using rediss:// for SSL
            if parsed.scheme == 'https':
                # Convert https:// to rediss://
                redis_url = redis_url.replace('https://', 'rediss://')
                parsed = urlparse(redis_url)
            
            # Extract connection details
            host = parsed.hostname
            port = parsed.port or 6379
            # Password is in the URL as: rediss://:password@host or rediss://default:password@host
            password = parsed.password
            if not password and '@' in parsed.netloc:
                # Try to extract from netloc if password not in parsed.password
                parts = parsed.netloc.split('@')
                if len(parts) > 1:
                    auth_part = parts[0]
                    if ':' in auth_part:
                        password = auth_part.split(':')[1] if auth_part.split(':')[0] else auth_part.split(':')[1]
            
            # Always use CERT_NONE for Upstash (they use self-signed certs)
            _redis_client = redis.Redis(
                host=host,
                port=port,
                password=password,
                decode_responses=decode_responses,
                ssl=True,
                ssl_cert_reqs=ssl.CERT_NONE,  # Upstash uses self-signed certs
                ssl_ca_certs=None,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
        else:
            # Standard Redis connection (no SSL)
            _redis_client = redis.from_url(
                redis_url,
                decode_responses=decode_responses,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
        
        # Test connection
        _redis_client.ping()
        logger.info("✅ Shared Redis connection pool established")
        
        return _redis_client
        
    except Exception as e:
        if os.getenv('FLASK_ENV') != 'production':
            logger.warning(f"Redis connection failed (using fallback): {e}")
        else:
            logger.error(f"❌ Redis connection failed: {e}")
        _redis_client = None
        return None

def reset_redis_client():
    """Reset the global Redis client (useful for testing)"""
    global _redis_client
    if _redis_client:
        try:
            _redis_client.close()
        except Exception:
            pass
    _redis_client = None
