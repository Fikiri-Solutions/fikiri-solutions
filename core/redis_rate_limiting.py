#!/usr/bin/env python3
"""
Redis Rate Limiting Middleware for Fikiri Solutions
Distributed rate limiting across all server instances
"""

import time
import logging
from typing import Dict, Any, Optional
from functools import wraps

# Optional Redis integration
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

try:
    from flask import request, jsonify, g
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    request = None
    jsonify = None
    g = None

try:
    from core.minimal_config import get_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    get_config = None

logger = logging.getLogger(__name__)

class RedisRateLimiter:
    """Redis-based rate limiter for distributed systems"""
    
    def __init__(self):
        self.config = get_config()
        self.redis_client = None
        self.rate_limit_prefix = "fikiri:rate_limit:"
        self._connect()
    
    def _connect(self):
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using in-memory rate limiting")
            self.redis_client = None
            return
            
        try:
            # Use centralized Redis connection pool
            from core.redis_pool import get_redis_client
            self.redis_client = get_redis_client()
            
            if self.redis_client:
                self.redis_client.ping()
                logger.info("✅ Redis rate limiter connected via pool")
            
        except Exception as e:
            logger.error(f"❌ Redis rate limiter connection failed: {e}")
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
    
    def _get_client_identifier(self) -> str:
        """Get client identifier for rate limiting"""
        # Try to get user ID from session first
        if hasattr(g, 'user_id') and g.user_id:
            return f"user:{g.user_id}"
        
        # Fall back to IP address
        return f"ip:{request.remote_addr}"
    
    def check_rate_limit(self, 
                        identifier: str = None, 
                        limit: int = 100, 
                        window: int = 3600,
                        per_route: bool = False) -> Dict[str, Any]:
        """Check rate limit for identifier"""
        if not self.is_connected():
            return {
                'allowed': True,
                'remaining': limit,
                'reset_time': time.time() + window,
                'limit': limit,
                'window': window
            }
        
        try:
            # Use provided identifier or get from request
            if not identifier:
                identifier = self._get_client_identifier()
            
            # Add route-specific identifier if requested
            if per_route:
                route = request.endpoint or 'unknown'
                identifier = f"{identifier}:{route}"
            
            # Create rate limit key
            key = f"{self.rate_limit_prefix}{identifier}"
            
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
                'current_count': current_count,
                'limit': limit,
                'window': window,
                'identifier': identifier
            }
            
        except Exception as e:
            logger.error(f"❌ Rate limit check failed: {e}")
            return {
                'allowed': True,
                'remaining': limit,
                'reset_time': time.time() + window,
                'limit': limit,
                'window': window
            }
    
    def get_rate_limit_status(self, identifier: str = None) -> Dict[str, Any]:
        """Get current rate limit status without incrementing"""
        if not self.is_connected():
            return {'current_count': 0, 'limit': 100, 'window': 3600}
        
        try:
            if not identifier:
                identifier = self._get_client_identifier()
            
            key = f"{self.rate_limit_prefix}{identifier}"
            current_count = self.redis_client.get(key) or 0
            ttl = self.redis_client.ttl(key)
            
            return {
                'current_count': int(current_count),
                'ttl': ttl,
                'identifier': identifier
            }
            
        except Exception as e:
            logger.error(f"❌ Rate limit status failed: {e}")
            return {'current_count': 0, 'ttl': -1}
    
    def reset_rate_limit(self, identifier: str = None) -> bool:
        """Reset rate limit for identifier"""
        if not self.is_connected():
            return False
        
        try:
            if not identifier:
                identifier = self._get_client_identifier()
            
            key = f"{self.rate_limit_prefix}{identifier}"
            result = self.redis_client.delete(key)
            logger.info(f"✅ Reset rate limit for: {identifier}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"❌ Rate limit reset failed: {e}")
            return False
    
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        if not self.is_connected():
            return {}
        
        try:
            pattern = f"{self.rate_limit_prefix}*"
            rate_limit_keys = self.redis_client.keys(pattern)
            
            stats = {
                'total_rate_limits': len(rate_limit_keys),
                'active_identifiers': len(set(key.split(':')[-1] for key in rate_limit_keys))
            }
            
            # Analyze rate limit usage
            total_requests = 0
            for key in rate_limit_keys:
                count = self.redis_client.get(key) or 0
                total_requests += int(count)
            
            stats['total_requests_tracked'] = total_requests
            stats['average_requests_per_identifier'] = total_requests / max(1, len(rate_limit_keys))
            
            logger.info(f"✅ Rate limit stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Rate limit stats failed: {e}")
            return {}

# Global rate limiter
rate_limiter = RedisRateLimiter()

def get_rate_limiter() -> RedisRateLimiter:
    """Get global rate limiter"""
    return rate_limiter

# Flask middleware integration
def init_rate_limiting(app):
    """Initialize rate limiting middleware"""
    
    @app.before_request
    def check_rate_limit():
        """Check rate limit before each request"""
        # Skip rate limiting for static files
        if request.endpoint and request.endpoint.startswith('static'):
            return
        
        # Skip rate limiting for health check endpoints
        if request.path == '/api/health' or request.path == '/health':
            return
        
        # Get rate limit configuration
        rate_limit_config = get_rate_limit_config(request.endpoint)
        
        if rate_limit_config:
            result = rate_limiter.check_rate_limit(
                limit=rate_limit_config['limit'],
                window=rate_limit_config['window'],
                per_route=rate_limit_config.get('per_route', False)
            )
            
            # Store rate limit info in g for response headers
            g.rate_limit_info = result
            
            if not result['allowed']:
                logger.warning(f"Rate limit exceeded for {result['identifier']}")
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Limit: {result["limit"]} per {result["window"]} seconds',
                    'retry_after': int(result['reset_time'] - time.time())
                }), 429
    
    @app.after_request
    def add_rate_limit_headers(response):
        """Add rate limit headers to response"""
        if hasattr(g, 'rate_limit_info'):
            info = g.rate_limit_info
            response.headers['X-RateLimit-Limit'] = str(info['limit'])
            response.headers['X-RateLimit-Remaining'] = str(info['remaining'])
            response.headers['X-RateLimit-Reset'] = str(int(info['reset_time']))
            response.headers['X-RateLimit-Window'] = str(info['window'])
        
        return response

def get_rate_limit_config(endpoint: str) -> Optional[Dict[str, Any]]:
    """Get rate limit configuration for endpoint"""
    
    # Default rate limits
    default_limits = {
        'api': {'limit': 1000, 'window': 3600},  # 1000 requests per hour
        'auth': {'limit': 10, 'window': 300},    # 10 requests per 5 minutes
        'ai': {'limit': 100, 'window': 3600},    # 100 AI requests per hour
        'email': {'limit': 50, 'window': 3600},  # 50 email operations per hour
        'crm': {'limit': 200, 'window': 3600},   # 200 CRM operations per hour
    }
    
    # Endpoint-specific limits
    endpoint_limits = {
        'login': {'limit': 5, 'window': 300},     # 5 login attempts per 5 minutes
        'register': {'limit': 3, 'window': 300},  # 3 registrations per 5 minutes
        'password_reset': {'limit': 3, 'window': 300},  # 3 password resets per 5 minutes
        'ai_generate': {'limit': 50, 'window': 3600},   # 50 AI generations per hour
        'email_send': {'limit': 20, 'window': 3600},   # 20 emails per hour
        'webhook': {'limit': 1000, 'window': 3600},    # 1000 webhooks per hour
    }
    
    # Check endpoint-specific limits first
    if endpoint in endpoint_limits:
        return endpoint_limits[endpoint]
    
    # Check category limits
    for category, config in default_limits.items():
        if endpoint and category in endpoint:
            return config
    
    # Return default API limit
    return default_limits['api']

# Decorator for custom rate limiting
def rate_limit(limit: int = 100, window: int = 3600, per_route: bool = False):
    """Decorator for custom rate limiting"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = rate_limiter.check_rate_limit(
                limit=limit,
                window=window,
                per_route=per_route
            )
            
            if not result['allowed']:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Limit: {limit} per {window} seconds',
                    'retry_after': int(result['reset_time'] - time.time())
                }), 429
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# Admin functions
def get_all_rate_limits() -> Dict[str, Any]:
    """Get all active rate limits (admin function)"""
    if not rate_limiter.is_connected():
        return {}
    
    try:
        pattern = f"{rate_limiter.rate_limit_prefix}*"
        keys = rate_limiter.redis_client.keys(pattern)
        
        rate_limits = {}
        for key in keys:
            identifier = key.replace(rate_limiter.rate_limit_prefix, '')
            count = rate_limiter.redis_client.get(key) or 0
            ttl = rate_limiter.redis_client.ttl(key)
            
            rate_limits[identifier] = {
                'current_count': int(count),
                'ttl': ttl,
                'expires_at': time.time() + ttl if ttl > 0 else None
            }
        
        return rate_limits
        
    except Exception as e:
        logger.error(f"❌ Get all rate limits failed: {e}")
        return {}

def reset_all_rate_limits() -> bool:
    """Reset all rate limits (admin function)"""
    if not rate_limiter.is_connected():
        return False
    
    try:
        pattern = f"{rate_limiter.rate_limit_prefix}*"
        keys = rate_limiter.redis_client.keys(pattern)
        
        if keys:
            rate_limiter.redis_client.delete(*keys)
            logger.info(f"✅ Reset {len(keys)} rate limits")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Reset all rate limits failed: {e}")
        return False
