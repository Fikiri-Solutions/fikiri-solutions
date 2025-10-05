#!/usr/bin/env python3
"""
Enhanced Rate Limiting System
Advanced rate limiting with Redis backend, sliding window, and per-user limits
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass
from enum import Enum

# Optional Redis integration
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

class RateLimitType(Enum):
    """Rate limit type enumeration"""
    GLOBAL = "global"
    USER = "user"
    IP = "ip"
    ENDPOINT = "endpoint"
    CUSTOM = "custom"

@dataclass
class RateLimit:
    """Rate limit configuration"""
    name: str
    limit_type: RateLimitType
    max_requests: int
    window_seconds: int
    key_prefix: str = ""
    description: str = ""

@dataclass
class RateLimitResult:
    """Rate limit check result"""
    allowed: bool
    remaining: int
    reset_time: int
    retry_after: int = 0
    limit: int = 0

class EnhancedRateLimiter:
    """Enhanced rate limiting system with Redis backend"""
    
    def __init__(self):
        self.redis_client = None
        self.key_prefix = "fikiri:rate_limit:"
        self.default_limits = {
            'api_global': RateLimit('api_global', RateLimitType.GLOBAL, 1000, 3600, 'API global limit'),
            'api_user': RateLimit('api_user', RateLimitType.USER, 100, 3600, 'API per user limit'),
            'api_ip': RateLimit('api_ip', RateLimitType.IP, 200, 3600, 'API per IP limit'),
            'login_attempts': RateLimit('login_attempts', RateLimitType.IP, 20, 900, 'Login attempts per IP'),
            'signup_attempts': RateLimit('signup_attempts', RateLimitType.IP, 3, 3600, 'Signup attempts per IP'),
            'email_send': RateLimit('email_send', RateLimitType.USER, 50, 3600, 'Email sending per user'),
            'gmail_sync': RateLimit('gmail_sync', RateLimitType.USER, 10, 3600, 'Gmail sync per user'),
            'onboarding': RateLimit('onboarding', RateLimitType.USER, 20, 3600, 'Onboarding operations per user')
        }
        self._connect_redis()
        self._initialize_tables()
    
    def _connect_redis(self):
        """Connect to Redis for rate limiting"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using in-memory rate limiting")
            return
        
        try:
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
            else:
                self.redis_client = redis.Redis(
                    host=os.getenv('REDIS_HOST', 'localhost'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    password=os.getenv('REDIS_PASSWORD'),
                    db=int(os.getenv('REDIS_DB', 0)),
                    decode_responses=True
                )
            
            self.redis_client.ping()
            logger.info("✅ Enhanced rate limiter Redis connection established")
            
        except Exception as e:
            logger.error(f"❌ Enhanced rate limiter Redis connection failed: {e}")
            self.redis_client = None
    
    def _initialize_tables(self):
        """Initialize database tables for rate limit tracking"""
        try:
            # Create rate limit violations table
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS rate_limit_violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    limit_name TEXT NOT NULL,
                    limit_type TEXT NOT NULL,
                    identifier TEXT NOT NULL,
                    ip_address TEXT,
                    user_id INTEGER,
                    endpoint TEXT,
                    violation_count INTEGER DEFAULT 1,
                    first_violation DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_violation DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_blocked BOOLEAN DEFAULT FALSE,
                    block_until DATETIME,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """, fetch=False)
            
            # Create indexes
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_rate_limit_violations_identifier 
                ON rate_limit_violations (identifier)
            """, fetch=False)
            
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_rate_limit_violations_user_id 
                ON rate_limit_violations (user_id)
            """, fetch=False)
            
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_rate_limit_violations_ip_address 
                ON rate_limit_violations (ip_address)
            """, fetch=False)
            
            logger.info("✅ Rate limiter tables initialized")
            
        except Exception as e:
            logger.error(f"❌ Rate limiter table initialization failed: {e}")
    
    def check_rate_limit(self, limit_name: str, identifier: str, 
                        ip_address: str = None, user_id: int = None,
                        endpoint: str = None) -> RateLimitResult:
        """Check if request is within rate limit"""
        try:
            # Get rate limit configuration
            rate_limit = self.default_limits.get(limit_name)
            if not rate_limit:
                # Allow if no limit configured
                return RateLimitResult(
                    allowed=True,
                    remaining=999999,
                    reset_time=int(time.time() + 3600),
                    limit=999999
                )
            
            # Generate rate limit key
            key = self._generate_rate_limit_key(rate_limit, identifier, ip_address, user_id, endpoint)
            
            # Check rate limit
            if self.redis_client:
                result = self._check_redis_rate_limit(key, rate_limit)
            else:
                result = self._check_database_rate_limit(key, rate_limit)
            
            # Log violation if rate limit exceeded
            if not result.allowed:
                self._log_rate_limit_violation(
                    limit_name, rate_limit.limit_type, identifier,
                    ip_address, user_id, endpoint
                )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Rate limit check failed: {e}")
            # Allow request if rate limiting fails
            return RateLimitResult(
                allowed=True,
                remaining=999999,
                reset_time=int(time.time() + 3600),
                limit=999999
            )
    
    def _generate_rate_limit_key(self, rate_limit: RateLimit, identifier: str,
                                ip_address: str = None, user_id: int = None,
                                endpoint: str = None) -> str:
        """Generate rate limit key based on type"""
        key_parts = [self.key_prefix, rate_limit.name]
        
        if rate_limit.limit_type == RateLimitType.GLOBAL:
            key_parts.append("global")
        elif rate_limit.limit_type == RateLimitType.USER:
            key_parts.append(f"user:{user_id or identifier}")
        elif rate_limit.limit_type == RateLimitType.IP:
            key_parts.append(f"ip:{ip_address or identifier}")
        elif rate_limit.limit_type == RateLimitType.ENDPOINT:
            key_parts.append(f"endpoint:{endpoint or identifier}")
        else:
            key_parts.append(f"custom:{identifier}")
        
        if rate_limit.key_prefix:
            key_parts.append(rate_limit.key_prefix)
        
        return ":".join(key_parts)
    
    def _check_redis_rate_limit(self, key: str, rate_limit: RateLimit) -> RateLimitResult:
        """Check rate limit using Redis sliding window"""
        try:
            current_time = time.time()
            window_start = current_time - rate_limit.window_seconds
            
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Remove expired entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, rate_limit.window_seconds)
            
            # Execute pipeline
            results = pipe.execute()
            
            current_count = results[1] + 1  # +1 for the request we just added
            
            allowed = current_count <= rate_limit.max_requests
            remaining = max(0, rate_limit.max_requests - current_count)
            reset_time = int(current_time + rate_limit.window_seconds)
            retry_after = 0 if allowed else int(rate_limit.window_seconds)
            
            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset_time=reset_time,
                retry_after=retry_after,
                limit=rate_limit.max_requests
            )
            
        except Exception as e:
            logger.error(f"❌ Redis rate limit check failed: {e}")
            # Fallback to database
            return self._check_database_rate_limit(key, rate_limit)
    
    def _check_database_rate_limit(self, key: str, rate_limit: RateLimit) -> RateLimitResult:
        """Check rate limit using database (fallback)"""
        try:
            current_time = datetime.utcnow()
            window_start = current_time - timedelta(seconds=rate_limit.window_seconds)
            
            # Count requests in window
            count_result = db_optimizer.execute_query("""
                SELECT COUNT(*) as count FROM rate_limit_violations 
                WHERE identifier = ? AND last_violation > ?
            """, (key, window_start.isoformat()))
            
            current_count = count_result[0]['count'] if count_result else 0
            
            allowed = current_count < rate_limit.max_requests
            remaining = max(0, rate_limit.max_requests - current_count - 1)
            reset_time = int(time.time() + rate_limit.window_seconds)
            retry_after = 0 if allowed else rate_limit.window_seconds
            
            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset_time=reset_time,
                retry_after=retry_after,
                limit=rate_limit.max_requests
            )
            
        except Exception as e:
            logger.error(f"❌ Database rate limit check failed: {e}")
            # Allow request if database check fails
            return RateLimitResult(
                allowed=True,
                remaining=999999,
                reset_time=int(time.time() + 3600),
                limit=999999
            )
    
    def _log_rate_limit_violation(self, limit_name: str, limit_type: RateLimitType,
                                 identifier: str, ip_address: str = None,
                                 user_id: int = None, endpoint: str = None):
        """Log rate limit violation"""
        try:
            # Check if violation already exists
            existing = db_optimizer.execute_query("""
                SELECT id, violation_count FROM rate_limit_violations 
                WHERE identifier = ? AND limit_name = ?
            """, (identifier, limit_name))
            
            if existing:
                # Update existing violation
                violation_id = existing[0]['id']
                new_count = existing[0]['violation_count'] + 1
                
                db_optimizer.execute_query("""
                    UPDATE rate_limit_violations 
                    SET violation_count = ?, last_violation = datetime('now')
                    WHERE id = ?
                """, (new_count, violation_id), fetch=False)
            else:
                # Create new violation record
                db_optimizer.execute_query("""
                    INSERT INTO rate_limit_violations 
                    (limit_name, limit_type, identifier, ip_address, user_id, endpoint, violation_count)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (
                    limit_name,
                    limit_type.value,
                    identifier,
                    ip_address,
                    user_id,
                    endpoint
                ), fetch=False)
            
            logger.warning(f"⚠️ Rate limit violated: {limit_name} for {identifier}")
            
        except Exception as e:
            logger.error(f"❌ Rate limit violation logging failed: {e}")
    
    def get_rate_limit_status(self, limit_name: str, identifier: str,
                             ip_address: str = None, user_id: int = None,
                             endpoint: str = None) -> Dict[str, Any]:
        """Get current rate limit status"""
        try:
            rate_limit = self.default_limits.get(limit_name)
            if not rate_limit:
                return {'error': 'Rate limit not found'}
            
            key = self._generate_rate_limit_key(rate_limit, identifier, ip_address, user_id, endpoint)
            
            if self.redis_client:
                current_time = time.time()
                window_start = current_time - rate_limit.window_seconds
                
                # Get current count
                current_count = self.redis_client.zcount(key, window_start, current_time)
                
                return {
                    'limit_name': limit_name,
                    'current_count': current_count,
                    'limit': rate_limit.max_requests,
                    'remaining': max(0, rate_limit.max_requests - current_count),
                    'window_seconds': rate_limit.window_seconds,
                    'reset_time': int(current_time + rate_limit.window_seconds)
                }
            else:
                # Database fallback
                current_time = datetime.utcnow()
                window_start = current_time - timedelta(seconds=rate_limit.window_seconds)
                
                count_result = db_optimizer.execute_query("""
                    SELECT COUNT(*) as count FROM rate_limit_violations 
                    WHERE identifier = ? AND last_violation > ?
                """, (key, window_start.isoformat()))
                
                current_count = count_result[0]['count'] if count_result else 0
                
                return {
                    'limit_name': limit_name,
                    'current_count': current_count,
                    'limit': rate_limit.max_requests,
                    'remaining': max(0, rate_limit.max_requests - current_count),
                    'window_seconds': rate_limit.window_seconds,
                    'reset_time': int(time.time() + rate_limit.window_seconds)
                }
                
        except Exception as e:
            logger.error(f"❌ Rate limit status retrieval failed: {e}")
            return {'error': str(e)}
    
    def reset_rate_limit(self, limit_name: str, identifier: str,
                        ip_address: str = None, user_id: int = None,
                        endpoint: str = None) -> bool:
        """Reset rate limit for identifier"""
        try:
            rate_limit = self.default_limits.get(limit_name)
            if not rate_limit:
                return False
            
            key = self._generate_rate_limit_key(rate_limit, identifier, ip_address, user_id, endpoint)
            
            # Reset in Redis
            if self.redis_client:
                self.redis_client.delete(key)
            
            # Reset in database
            db_optimizer.execute_query("""
                DELETE FROM rate_limit_violations 
                WHERE identifier = ? AND limit_name = ?
            """, (key, limit_name), fetch=False)
            
            logger.info(f"✅ Rate limit reset: {limit_name} for {identifier}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Rate limit reset failed: {e}")
            return False
    
    def cleanup_expired_violations(self):
        """Clean up expired rate limit violations"""
        try:
            # Clean database violations older than 7 days
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            db_optimizer.execute_query("""
                DELETE FROM rate_limit_violations 
                WHERE last_violation < ?
            """, (cutoff_date.isoformat(),), fetch=False)
            
            logger.info("✅ Expired rate limit violations cleaned up")
            
        except Exception as e:
            logger.error(f"❌ Rate limit violation cleanup failed: {e}")
    
    def get_violation_stats(self) -> Dict[str, Any]:
        """Get rate limit violation statistics"""
        try:
            stats = db_optimizer.execute_query("""
                SELECT 
                    limit_name,
                    COUNT(*) as violation_count,
                    SUM(violation_count) as total_violations,
                    MAX(last_violation) as last_violation
                FROM rate_limit_violations 
                WHERE last_violation > datetime('now', '-24 hours')
                GROUP BY limit_name
                ORDER BY total_violations DESC
            """)
            
            return {
                'violations_by_limit': [
                    {
                        'limit_name': stat['limit_name'],
                        'violation_count': stat['violation_count'],
                        'total_violations': stat['total_violations'],
                        'last_violation': stat['last_violation']
                    }
                    for stat in stats
                ],
                'total_violations': sum(stat['total_violations'] for stat in stats) if stats else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Rate limit violation stats failed: {e}")
            return {}

# Global rate limiter
enhanced_rate_limiter = EnhancedRateLimiter()

# Decorator for rate limiting
def rate_limit(limit_name: str, identifier_func: Callable = None):
    """Decorator to apply rate limiting to functions"""
    def decorator(func):
        from functools import wraps
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate identifier
            if identifier_func:
                identifier = identifier_func(*args, **kwargs)
            else:
                # Default identifier generation
                identifier = "default"
            
            # Get request context
            from flask import request
            ip_address = request.remote_addr if request else None
            user_id = kwargs.get('user_id')
            endpoint = request.endpoint if request else None
            
            # Check rate limit
            result = enhanced_rate_limiter.check_rate_limit(
                limit_name, identifier, ip_address, user_id, endpoint
            )
            
            if not result.allowed:
                from flask import jsonify
                return jsonify({
                    'success': False,
                    'error': 'Rate limit exceeded',
                    'error_code': 'RATE_LIMIT_EXCEEDED',
                    'retry_after': result.retry_after,
                    'limit': result.limit,
                    'remaining': result.remaining
                }), 429
            
            # Execute function
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

# Helper functions for common rate limiting patterns
def check_api_rate_limit(user_id: int = None, ip_address: str = None) -> RateLimitResult:
    """Check API rate limit"""
    identifier = f"user:{user_id}" if user_id else f"ip:{ip_address}"
    return enhanced_rate_limiter.check_rate_limit('api_user', identifier, ip_address, user_id)

def check_login_rate_limit(ip_address: str) -> RateLimitResult:
    """Check login rate limit"""
    return enhanced_rate_limiter.check_rate_limit('login_attempts', ip_address, ip_address)

def check_signup_rate_limit(ip_address: str) -> RateLimitResult:
    """Check signup rate limit"""
    return enhanced_rate_limiter.check_rate_limit('signup_attempts', ip_address, ip_address)

def check_email_send_rate_limit(user_id: int) -> RateLimitResult:
    """Check email sending rate limit"""
    return enhanced_rate_limiter.check_rate_limit('email_send', f"user:{user_id}", user_id=user_id)

def check_gmail_sync_rate_limit(user_id: int) -> RateLimitResult:
    """Check Gmail sync rate limit"""
    return enhanced_rate_limiter.check_rate_limit('gmail_sync', f"user:{user_id}", user_id=user_id)