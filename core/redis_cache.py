#!/usr/bin/env python3
"""
Redis Production Cache Layer for Fikiri Solutions
High-performance caching for AI responses, email parsing, and lead scoring
"""

import redis
import json
import time
import hashlib
import logging
from typing import Optional, Dict, Any, List, Union
from functools import wraps
from core.minimal_config import get_config

logger = logging.getLogger(__name__)

class FikiriCache:
    """Production Redis cache layer for Fikiri Solutions"""
    
    def __init__(self):
        self.config = get_config()
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """Connect to Redis Cloud"""
        try:
            if self.config.redis_url:
                self.redis_client = redis.from_url(
                    self.config.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
            else:
                self.redis_client = redis.Redis(
                    host=self.config.redis_host,
                    port=self.config.redis_port,
                    password=self.config.redis_password,
                    db=self.config.redis_db,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
            
            # Test connection
            self.redis_client.ping()
            logger.info("✅ Redis cache layer connected successfully")
            
        except Exception as e:
            logger.error(f"❌ Redis cache connection failed: {e}")
            self.redis_client = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def _generate_cache_key(self, prefix: str, identifier: str, *args) -> str:
        """Generate consistent cache keys"""
        # Create hash of additional arguments for uniqueness
        if args:
            args_hash = hashlib.md5(str(args).encode()).hexdigest()[:8]
            return f"fikiri:{prefix}:{identifier}:{args_hash}"
        return f"fikiri:{prefix}:{identifier}"
    
    # AI Response Caching
    def cache_ai_response(self, prompt: str, response: str, user_id: str, ttl: int = 300) -> bool:
        """Cache AI response with semantic key"""
        if not self.is_connected():
            return False
        
        try:
            # Create semantic key based on prompt content
            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:16]
            key = self._generate_cache_key("ai", f"{user_id}:{prompt_hash}")
            
            cache_data = {
                'prompt': prompt,
                'response': response,
                'user_id': user_id,
                'timestamp': time.time(),
                'ttl': ttl
            }
            
            self.redis_client.setex(key, ttl, json.dumps(cache_data))
            logger.info(f"✅ Cached AI response for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ AI response cache failed: {e}")
            return False
    
    def get_cached_ai_response(self, prompt: str, user_id: str) -> Optional[str]:
        """Get cached AI response"""
        if not self.is_connected():
            return None
        
        try:
            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:16]
            key = self._generate_cache_key("ai", f"{user_id}:{prompt_hash}")
            
            cached_data = self.redis_client.get(key)
            if cached_data:
                data = json.loads(cached_data)
                logger.info(f"✅ Cache hit for AI response (user {user_id})")
                return data['response']
            
            return None
            
        except Exception as e:
            logger.error(f"❌ AI response cache retrieval failed: {e}")
            return None
    
    # Email Parsing Cache
    def cache_email_parse(self, email_content: str, parsed_data: Dict[str, Any], ttl: int = 1800) -> bool:
        """Cache parsed email data"""
        if not self.is_connected():
            return False
        
        try:
            email_hash = hashlib.md5(email_content.encode()).hexdigest()[:16]
            key = self._generate_cache_key("email", f"parse:{email_hash}")
            
            cache_data = {
                'email_content': email_content,
                'parsed_data': parsed_data,
                'timestamp': time.time(),
                'ttl': ttl
            }
            
            self.redis_client.setex(key, ttl, json.dumps(cache_data))
            logger.info("✅ Cached email parse result")
            return True
            
        except Exception as e:
            logger.error(f"❌ Email parse cache failed: {e}")
            return False
    
    def get_cached_email_parse(self, email_content: str) -> Optional[Dict[str, Any]]:
        """Get cached email parse data"""
        if not self.is_connected():
            return None
        
        try:
            email_hash = hashlib.md5(email_content.encode()).hexdigest()[:16]
            key = self._generate_cache_key("email", f"parse:{email_hash}")
            
            cached_data = self.redis_client.get(key)
            if cached_data:
                data = json.loads(cached_data)
                logger.info("✅ Cache hit for email parse")
                return data['parsed_data']
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Email parse cache retrieval failed: {e}")
            return None
    
    # Lead Scoring Cache
    def cache_lead_score(self, lead_data: Dict[str, Any], score: float, ttl: int = 3600) -> bool:
        """Cache lead scoring results"""
        if not self.is_connected():
            return False
        
        try:
            # Create key from lead email and company
            lead_key = f"{lead_data.get('email', '')}:{lead_data.get('company', '')}"
            lead_hash = hashlib.md5(lead_key.encode()).hexdigest()[:16]
            key = self._generate_cache_key("lead", f"score:{lead_hash}")
            
            cache_data = {
                'lead_data': lead_data,
                'score': score,
                'timestamp': time.time(),
                'ttl': ttl
            }
            
            self.redis_client.setex(key, ttl, json.dumps(cache_data))
            logger.info(f"✅ Cached lead score: {score}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Lead score cache failed: {e}")
            return False
    
    def get_cached_lead_score(self, lead_data: Dict[str, Any]) -> Optional[float]:
        """Get cached lead score"""
        if not self.is_connected():
            return None
        
        try:
            lead_key = f"{lead_data.get('email', '')}:{lead_data.get('company', '')}"
            lead_hash = hashlib.md5(lead_key.encode()).hexdigest()[:16]
            key = self._generate_cache_key("lead", f"score:{lead_hash}")
            
            cached_data = self.redis_client.get(key)
            if cached_data:
                data = json.loads(cached_data)
                logger.info("✅ Cache hit for lead score")
                return data['score']
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Lead score cache retrieval failed: {e}")
            return None
    
    # User Session Cache
    def cache_user_session(self, session_id: str, session_data: Dict[str, Any], ttl: int = 86400) -> bool:
        """Cache user session data"""
        if not self.is_connected():
            return False
        
        try:
            key = self._generate_cache_key("session", session_id)
            
            cache_data = {
                'session_data': session_data,
                'timestamp': time.time(),
                'ttl': ttl
            }
            
            self.redis_client.setex(key, ttl, json.dumps(cache_data))
            logger.info(f"✅ Cached user session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ User session cache failed: {e}")
            return False
    
    def get_cached_user_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user session data"""
        if not self.is_connected():
            return None
        
        try:
            key = self._generate_cache_key("session", session_id)
            
            cached_data = self.redis_client.get(key)
            if cached_data:
                data = json.loads(cached_data)
                logger.info(f"✅ Cache hit for user session: {session_id}")
                return data['session_data']
            
            return None
            
        except Exception as e:
            logger.error(f"❌ User session cache retrieval failed: {e}")
            return None
    
    def delete_user_session(self, session_id: str) -> bool:
        """Delete user session"""
        if not self.is_connected():
            return False
        
        try:
            key = self._generate_cache_key("session", session_id)
            result = self.redis_client.delete(key)
            logger.info(f"✅ Deleted user session: {session_id}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"❌ User session deletion failed: {e}")
            return False
    
    # Rate Limiting
    def check_rate_limit(self, identifier: str, limit: int, window: int) -> Dict[str, Any]:
        """Check rate limit for identifier"""
        if not self.is_connected():
            return {'allowed': True, 'remaining': limit, 'reset_time': time.time() + window}
        
        try:
            key = self._generate_cache_key("rate_limit", identifier)
            
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            results = pipe.execute()
            
            current_count = results[0]
            remaining = max(0, limit - current_count)
            reset_time = time.time() + window
            
            allowed = current_count <= limit
            
            logger.info(f"Rate limit check: {identifier} = {current_count}/{limit} (allowed: {allowed})")
            
            return {
                'allowed': allowed,
                'remaining': remaining,
                'reset_time': reset_time,
                'current_count': current_count
            }
            
        except Exception as e:
            logger.error(f"❌ Rate limit check failed: {e}")
            return {'allowed': True, 'remaining': limit, 'reset_time': time.time() + window}
    
    # Cache Statistics
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.is_connected():
            return {}
        
        try:
            # Get all Fikiri cache keys
            ai_keys = self.redis_client.keys("fikiri:ai:*")
            email_keys = self.redis_client.keys("fikiri:email:*")
            lead_keys = self.redis_client.keys("fikiri:lead:*")
            session_keys = self.redis_client.keys("fikiri:session:*")
            rate_limit_keys = self.redis_client.keys("fikiri:rate_limit:*")
            
            # Get Redis info
            info = self.redis_client.info()
            
            return {
                'ai_responses_cached': len(ai_keys),
                'email_parses_cached': len(email_keys),
                'lead_scores_cached': len(lead_keys),
                'active_sessions': len(session_keys),
                'rate_limits_active': len(rate_limit_keys),
                'total_memory_used': info.get('used_memory_human', 'Unknown'),
                'connected_clients': info.get('connected_clients', 0),
                'cache_hit_rate': info.get('keyspace_hits', 0) / max(1, info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0))
            }
            
        except Exception as e:
            logger.error(f"❌ Cache stats failed: {e}")
            return {}
    
    # Cache Management
    def clear_cache(self, prefix: str = None) -> bool:
        """Clear cache by prefix or all"""
        if not self.is_connected():
            return False
        
        try:
            if prefix:
                pattern = f"fikiri:{prefix}:*"
            else:
                pattern = "fikiri:*"
            
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"✅ Cleared {len(keys)} cache keys matching '{pattern}'")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Cache clear failed: {e}")
            return False

# Global cache instance
fikiri_cache = FikiriCache()

def get_cache() -> FikiriCache:
    """Get global cache instance"""
    return fikiri_cache

# Decorator for automatic caching
def cache_result(prefix: str, ttl: int = 300, key_func=None):
    """Decorator to automatically cache function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = cache.redis_client.get(f"fikiri:{prefix}:{cache_key}")
            if cached_result:
                logger.info(f"✅ Cache hit for {func.__name__}")
                return json.loads(cached_result)
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.redis_client.setex(f"fikiri:{prefix}:{cache_key}", ttl, json.dumps(result))
            logger.info(f"✅ Cached result for {func.__name__}")
            
            return result
        
        return wrapper
    return decorator
