#!/usr/bin/env python3
"""
Redis Service for Fikiri Solutions
Handles Redis Cloud connection and operations
"""

import redis
import json
import time
import logging
from typing import Optional, Dict, Any, List, Union
from core.minimal_config import get_config

logger = logging.getLogger(__name__)

class RedisService:
    """Redis service for caching, sessions, and data storage."""
    
    def __init__(self):
        """Initialize Redis connection."""
        self.config = get_config()
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """Connect to Redis Cloud."""
        try:
            if self.config.redis_url:
                # Use Redis URL if available
                self.redis_client = redis.from_url(
                    self.config.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            else:
                # Use individual connection parameters
                self.redis_client = redis.Redis(
                    host=self.config.redis_host,
                    port=self.config.redis_port,
                    password=self.config.redis_password,
                    db=self.config.redis_db,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            
            # Test connection
            self.redis_client.ping()
            logger.info("✅ Connected to Redis Cloud successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            self.redis_client = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        if not self.is_connected():
            return None
        try:
            return self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Set key-value pair with optional expiration."""
        if not self.is_connected():
            return False
        try:
            if expire:
                self.redis_client.setex(key, expire, value)
            else:
                self.redis_client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key."""
        if not self.is_connected():
            return False
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.is_connected():
            return False
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key."""
        if not self.is_connected():
            return False
        try:
            return bool(self.redis_client.expire(key, seconds))
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False
    
    # Hash operations
    def hset(self, key: str, field: str, value: str) -> bool:
        """Set hash field."""
        if not self.is_connected():
            return False
        try:
            self.redis_client.hset(key, field, value)
            return True
        except Exception as e:
            logger.error(f"Redis HSET error for key {key}, field {field}: {e}")
            return False
    
    def hget(self, key: str, field: str) -> Optional[str]:
        """Get hash field value."""
        if not self.is_connected():
            return None
        try:
            return self.redis_client.hget(key, field)
        except Exception as e:
            logger.error(f"Redis HGET error for key {key}, field {field}: {e}")
            return None
    
    def hgetall(self, key: str) -> Dict[str, str]:
        """Get all hash fields."""
        if not self.is_connected():
            return {}
        try:
            return self.redis_client.hgetall(key)
        except Exception as e:
            logger.error(f"Redis HGETALL error for key {key}: {e}")
            return {}
    
    def hmset(self, key: str, mapping: Dict[str, str]) -> bool:
        """Set multiple hash fields."""
        if not self.is_connected():
            return False
        try:
            self.redis_client.hset(key, mapping=mapping)
            return True
        except Exception as e:
            logger.error(f"Redis HMSET error for key {key}: {e}")
            return False
    
    # List operations
    def lpush(self, key: str, *values: str) -> bool:
        """Push values to list."""
        if not self.is_connected():
            return False
        try:
            self.redis_client.lpush(key, *values)
            return True
        except Exception as e:
            logger.error(f"Redis LPUSH error for key {key}: {e}")
            return False
    
    def rpush(self, key: str, *values: str) -> bool:
        """Push values to end of list."""
        if not self.is_connected():
            return False
        try:
            self.redis_client.rpush(key, *values)
            return True
        except Exception as e:
            logger.error(f"Redis RPUSH error for key {key}: {e}")
            return False
    
    def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get list range."""
        if not self.is_connected():
            return []
        try:
            return self.redis_client.lrange(key, start, end)
        except Exception as e:
            logger.error(f"Redis LRANGE error for key {key}: {e}")
            return []
    
    def llen(self, key: str) -> int:
        """Get list length."""
        if not self.is_connected():
            return 0
        try:
            return self.redis_client.llen(key)
        except Exception as e:
            logger.error(f"Redis LLEN error for key {key}: {e}")
            return 0
    
    # Set operations
    def sadd(self, key: str, *values: str) -> bool:
        """Add values to set."""
        if not self.is_connected():
            return False
        try:
            self.redis_client.sadd(key, *values)
            return True
        except Exception as e:
            logger.error(f"Redis SADD error for key {key}: {e}")
            return False
    
    def smembers(self, key: str) -> set:
        """Get all set members."""
        if not self.is_connected():
            return set()
        try:
            return self.redis_client.smembers(key)
        except Exception as e:
            logger.error(f"Redis SMEMBERS error for key {key}: {e}")
            return set()
    
    def sismember(self, key: str, value: str) -> bool:
        """Check if value is in set."""
        if not self.is_connected():
            return False
        try:
            return bool(self.redis_client.sismember(key, value))
        except Exception as e:
            logger.error(f"Redis SISMEMBER error for key {key}: {e}")
            return False
    
    # JSON operations (Redis Stack)
    def json_set(self, key: str, path: str, value: Any) -> bool:
        """Set JSON value."""
        if not self.is_connected():
            return False
        try:
            self.redis_client.json().set(key, path, value)
            return True
        except Exception as e:
            logger.error(f"Redis JSON SET error for key {key}: {e}")
            return False
    
    def json_get(self, key: str, path: str = "$") -> Any:
        """Get JSON value."""
        if not self.is_connected():
            return None
        try:
            return self.redis_client.json().get(key, path)
        except Exception as e:
            logger.error(f"Redis JSON GET error for key {key}: {e}")
            return None
    
    # Application-specific methods
    def store_user_data(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Store user data."""
        key = f"fikiri:user:{user_id}"
        return self.hmset(key, {k: str(v) for k, v in data.items()})
    
    def get_user_data(self, user_id: str) -> Dict[str, str]:
        """Get user data."""
        key = f"fikiri:user:{user_id}"
        return self.hgetall(key)
    
    def cache_ai_response(self, user_id: str, prompt: str, response: str) -> bool:
        """Cache AI response."""
        key = f"fikiri:ai_responses:{user_id}"
        data = {
            'prompt': prompt,
            'response': response,
            'timestamp': str(time.time())
        }
        return self.lpush(key, json.dumps(data))
    
    def get_ai_responses(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent AI responses."""
        key = f"fikiri:ai_responses:{user_id}"
        responses = self.lrange(key, 0, limit - 1)
        return [json.loads(r) for r in responses if r]
    
    def store_usage_analytics(self, user_id: str, date: str, data: Dict[str, Any]) -> bool:
        """Store usage analytics."""
        key = f"fikiri:usage:{user_id}:{date}"
        return self.hmset(key, {k: str(v) for k, v in data.items()})
    
    def get_usage_analytics(self, user_id: str, date: str) -> Dict[str, str]:
        """Get usage analytics."""
        key = f"fikiri:usage:{user_id}:{date}"
        return self.hgetall(key)
    
    def rate_limit_check(self, identifier: str, limit: int, window: int) -> bool:
        """Check rate limit."""
        key = f"fikiri:rate_limit:{identifier}"
        current = self.redis_client.incr(key)
        if current == 1:
            self.redis_client.expire(key, window)
        return current <= limit
    
    def get_info(self) -> Dict[str, Any]:
        """Get Redis server info."""
        if not self.is_connected():
            return {}
        try:
            return self.redis_client.info()
        except Exception as e:
            logger.error(f"Redis INFO error: {e}")
            return {}

# Global Redis service instance
redis_service = RedisService()

def get_redis_service() -> RedisService:
    """Get Redis service instance."""
    return redis_service
