#!/usr/bin/env python3
"""
Idempotency Management System
Ensures operations can be safely retried without side effects
"""

import os
import json
import time
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from functools import wraps

# Optional Redis integration
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

class IdempotencyManager:
    """Idempotency management system for safe operation retries"""
    
    def __init__(self):
        self.redis_client = None
        self.key_prefix = "fikiri:idempotency:"
        self.default_ttl = 24 * 60 * 60  # 24 hours
        self._connect_redis()
        self._initialize_tables()
    
    def _connect_redis(self):
        """Connect to Redis for idempotency keys"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using database for idempotency")
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
            logger.info("✅ Idempotency Redis connection established")
            
        except Exception as e:
            logger.error(f"❌ Idempotency Redis connection failed: {e}")
            self.redis_client = None
    
    def _initialize_tables(self):
        """Initialize database tables for idempotency tracking"""
        try:
            # Create idempotency keys table
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS idempotency_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_hash TEXT NOT NULL UNIQUE,
                    operation_type TEXT NOT NULL,
                    user_id INTEGER,
                    request_data TEXT,
                    response_data TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """, fetch=False)
            
            # Create indexes
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_idempotency_key_hash 
                ON idempotency_keys (key_hash)
            """, fetch=False)
            
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_idempotency_user_id 
                ON idempotency_keys (user_id)
            """, fetch=False)
            
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_idempotency_expires_at 
                ON idempotency_keys (expires_at)
            """, fetch=False)
            
            logger.info("✅ Idempotency tables initialized")
            
        except Exception as e:
            logger.error(f"❌ Idempotency table initialization failed: {e}")
    
    def generate_key(self, operation_type: str, user_id: int = None, 
                    request_data: Dict[str, Any] = None) -> str:
        """Generate an idempotency key"""
        try:
            # Create key components
            timestamp = str(int(time.time()))
            components = [operation_type, timestamp]
            
            if user_id:
                components.append(str(user_id))
            
            if request_data:
                # Include relevant request data for uniqueness
                data_str = json.dumps(request_data, sort_keys=True)
                components.append(data_str)
            
            # Generate key
            key_string = "|".join(components)
            key_hash = hashlib.sha256(key_string.encode()).hexdigest()
            
            return key_hash
            
        except Exception as e:
            logger.error(f"❌ Idempotency key generation failed: {e}")
            return None
    
    def check_key(self, key: str) -> Optional[Dict[str, Any]]:
        """Check if an idempotency key exists and return cached result"""
        try:
            # Try Redis first
            if self.redis_client:
                cached_result = self.redis_client.get(f"{self.key_prefix}{key}")
                if cached_result:
                    return json.loads(cached_result)
            
            # Fallback to database
            key_data = db_optimizer.execute_query("""
                SELECT * FROM idempotency_keys 
                WHERE key_hash = ? AND expires_at > datetime('now')
            """, (key,))
            
            if key_data:
                key_record = key_data[0]
                result = {
                    'key': key,
                    'status': key_record['status'],
                    'response_data': json.loads(key_record['response_data']) if key_record['response_data'] else None,
                    'created_at': key_record['created_at'],
                    'expires_at': key_record['expires_at']
                }
                
                # Cache in Redis
                if self.redis_client:
                    ttl = int((datetime.fromisoformat(key_record['expires_at']) - datetime.utcnow()).total_seconds())
                    if ttl > 0:
                        self.redis_client.setex(
                            f"{self.key_prefix}{key}",
                            ttl,
                            json.dumps(result)
                        )
                
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Idempotency key check failed: {e}")
            return None
    
    def store_key(self, key: str, operation_type: str, user_id: int = None,
                  request_data: Dict[str, Any] = None, ttl: int = None) -> bool:
        """Store an idempotency key"""
        try:
            ttl = ttl or self.default_ttl
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            
            # Store in database
            db_optimizer.execute_query("""
                INSERT OR REPLACE INTO idempotency_keys 
                (key_hash, operation_type, user_id, request_data, status, expires_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
            """, (
                key,
                operation_type,
                user_id,
                json.dumps(request_data) if request_data else None,
                expires_at.isoformat()
            ), fetch=False)
            
            # Cache in Redis
            if self.redis_client:
                self.redis_client.setex(
                    f"{self.key_prefix}{key}",
                    ttl,
                    json.dumps({
                        'key': key,
                        'status': 'pending',
                        'response_data': None,
                        'created_at': datetime.utcnow().isoformat(),
                        'expires_at': expires_at.isoformat()
                    })
                )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Idempotency key storage failed: {e}")
            return False
    
    def update_key_result(self, key: str, status: str, 
                         response_data: Dict[str, Any] = None) -> bool:
        """Update idempotency key with result"""
        try:
            # Update database
            db_optimizer.execute_query("""
                UPDATE idempotency_keys 
                SET status = ?, response_data = ?
                WHERE key_hash = ?
            """, (
                status,
                json.dumps(response_data) if response_data else None,
                key
            ), fetch=False)
            
            # Update Redis cache
            if self.redis_client:
                cached_result = self.redis_client.get(f"{self.key_prefix}{key}")
                if cached_result:
                    result = json.loads(cached_result)
                    result['status'] = status
                    result['response_data'] = response_data
                    
                    # Get remaining TTL
                    ttl = self.redis_client.ttl(f"{self.key_prefix}{key}")
                    if ttl > 0:
                        self.redis_client.setex(
                            f"{self.key_prefix}{key}",
                            ttl,
                            json.dumps(result)
                        )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Idempotency key update failed: {e}")
            return False
    
    def cleanup_expired_keys(self):
        """Clean up expired idempotency keys"""
        try:
            # Clean database
            db_optimizer.execute_query("""
                DELETE FROM idempotency_keys 
                WHERE expires_at < datetime('now')
            """, fetch=False)
            
            # Clean Redis (TTL handles expiration automatically)
            if self.redis_client:
                # Redis TTL handles expiration automatically
                pass
            
            logger.info("✅ Expired idempotency keys cleaned up")
            
        except Exception as e:
            logger.error(f"❌ Idempotency key cleanup failed: {e}")
    
    def get_key_stats(self) -> Dict[str, Any]:
        """Get idempotency key statistics"""
        try:
            stats = db_optimizer.execute_query("""
                SELECT 
                    COUNT(*) as total_keys,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_keys,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_keys,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_keys
                FROM idempotency_keys
                WHERE expires_at > datetime('now')
            """)
            
            if stats:
                return stats[0]
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ Idempotency key stats failed: {e}")
            return {}

# Global idempotency manager
idempotency_manager = IdempotencyManager()

# Decorator for idempotent operations
def idempotent(operation_type: str, ttl: int = None, key_generator: Callable = None):
    """Decorator to make functions idempotent"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate idempotency key
            if key_generator:
                key = key_generator(*args, **kwargs)
            else:
                # Default key generation
                request_data = {
                    'args': str(args),
                    'kwargs': {k: v for k, v in kwargs.items() if k not in ['user_id']}
                }
                user_id = kwargs.get('user_id')
                key = idempotency_manager.generate_key(operation_type, user_id, request_data)
            
            if not key:
                # If key generation fails, proceed without idempotency
                return func(*args, **kwargs)
            
            # Check if key exists
            cached_result = idempotency_manager.check_key(key)
            if cached_result:
                if cached_result['status'] == 'completed':
                    logger.info(f"✅ Idempotent operation {operation_type} returned cached result")
                    return cached_result['response_data']
                elif cached_result['status'] == 'failed':
                    logger.warning(f"⚠️ Idempotent operation {operation_type} previously failed")
                    return {'success': False, 'error': 'Operation previously failed'}
                else:
                    logger.info(f"⏳ Idempotent operation {operation_type} already in progress")
                    return {'success': False, 'error': 'Operation already in progress'}
            
            # Store key
            user_id = kwargs.get('user_id')
            request_data = {'args': str(args), 'kwargs': kwargs}
            idempotency_manager.store_key(key, operation_type, user_id, request_data, ttl)
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Update key with result
                if result and isinstance(result, dict):
                    status = 'completed' if result.get('success', True) else 'failed'
                else:
                    status = 'completed'
                
                idempotency_manager.update_key_result(key, status, result)
                
                return result
                
            except Exception as e:
                # Update key with error
                error_result = {'success': False, 'error': str(e)}
                idempotency_manager.update_key_result(key, 'failed', error_result)
                raise
        
        return wrapper
    return decorator

# Helper functions for common idempotency patterns
def generate_user_operation_key(operation_type: str, user_id: int, 
                               additional_data: Dict[str, Any] = None) -> str:
    """Generate idempotency key for user operations"""
    request_data = additional_data or {}
    return idempotency_manager.generate_key(operation_type, user_id, request_data)

def generate_email_operation_key(operation_type: str, user_id: int, 
                                email_id: str, action: str) -> str:
    """Generate idempotency key for email operations"""
    request_data = {
        'email_id': email_id,
        'action': action
    }
    return idempotency_manager.generate_key(operation_type, user_id, request_data)

def generate_contact_operation_key(operation_type: str, user_id: int, 
                                  contact_email: str, action: str) -> str:
    """Generate idempotency key for contact operations"""
    request_data = {
        'contact_email': contact_email,
        'action': action
    }
    return idempotency_manager.generate_key(operation_type, user_id, request_data)
