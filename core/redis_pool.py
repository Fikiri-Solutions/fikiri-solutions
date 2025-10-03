"""
Redis Connection Pool Manager
Provides centralized Redis connection pooling to prevent "max clients reached" errors.
"""

import redis
from redis.connection import ConnectionPool
import logging
import os
from typing import Optional
from core.minimal_config import get_config

logger = logging.getLogger(__name__)

# Global Redis connection pool
_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None

def get_redis_pool() -> ConnectionPool:
    """Get or create Redis connection pool."""
    global _redis_pool
    
    if _redis_pool is None:
        try:
            config = get_config()
            
            # Create connection pool with limits
            if config.redis_url:
                _redis_pool = ConnectionPool.from_url(
                    config.redis_url,
                    max_connections=10,  # Limit concurrent connections
                    retry_on_timeout=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    decode_responses=True
                )
            else:
                _redis_pool = ConnectionPool(
                    host=config.redis_host,
                    port=config.redis_port,
                    password=config.redis_password,
                    db=config.redis_db,
                    max_connections=10,  # Limit concurrent connections
                    retry_on_timeout=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    decode_responses=True
                )
            
            logger.info("✅ Redis connection pool created successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to create Redis connection pool: {e}")
            raise
    
    return _redis_pool

def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client using connection pool."""
    global _redis_client
    
    if _redis_client is None:
        try:
            pool = get_redis_pool()
            _redis_client = redis.Redis(connection_pool=pool)
            
            # Test connection
            _redis_client.ping()
            logger.info("✅ Redis client connected via pool")
            
        except Exception as e:
            logger.error(f"❌ Failed to create Redis client: {e}")
            return None
    
    return _redis_client

def is_redis_connected() -> bool:
    """Check if Redis is connected via pool."""
    try:
        client = get_redis_client()
        if client:
            client.ping()
            return True
        return False
    except Exception as e:
        logger.debug(f"Redis ping failed: {e}")
        return False

def close_redis_pool():
    """Close Redis connection pool and client."""
    global _redis_pool, _redis_client
    
    if _redis_client:
        try:
            _redis_client.close()
        except Exception:
            pass
        _redis_client = None
    
    if _redis_pool:
        try:
            _redis_pool.disconnect()
        except Exception:
            pass
        _redis_pool = None
    
    logger.info("✅ Redis connection pool closed")
