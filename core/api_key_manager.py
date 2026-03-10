"""
API Key Management System for External Client Authentication
Provides API key generation, validation, and tenant isolation
"""

import os
import secrets
import hashlib
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)


class APIKeyManager:
    """Manages API keys for external client authentication"""
    
    def __init__(self):
        self._initialize_tables()
    
    def _initialize_tables(self):
        """Initialize database tables for API key management"""
        try:
            # API keys table with tenant isolation
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    key_hash TEXT NOT NULL UNIQUE,
                    key_prefix TEXT NOT NULL,  -- First 8 chars for identification
                    name TEXT NOT NULL,  -- Human-readable name
                    description TEXT,
                    tenant_id TEXT,  -- Optional tenant identifier for multi-tenant isolation
                    scopes TEXT DEFAULT '["chatbot:query"]',  -- JSON array of allowed scopes
                    allowed_origins TEXT,  -- JSON array of allowed CORS origins (null = all)
                    rate_limit_per_minute INTEGER DEFAULT 60,
                    rate_limit_per_hour INTEGER DEFAULT 1000,
                    is_active BOOLEAN DEFAULT 1,
                    last_used_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """, fetch=False)
            
            # API key usage tracking for rate limiting
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS api_key_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    api_key_id INTEGER NOT NULL,
                    endpoint TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    response_status INTEGER,
                    response_time_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE
                )
            """, fetch=False)
            
            # Create indexes
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash 
                ON api_keys (key_hash)
            """, fetch=False)
            
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_api_keys_user_id 
                ON api_keys (user_id)
            """, fetch=False)
            
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_api_keys_tenant_id 
                ON api_keys (tenant_id)
            """, fetch=False)
            
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_api_key_usage_api_key_id 
                ON api_key_usage (api_key_id, created_at)
            """, fetch=False)
            
            # Migration: Add allowed_origins column if it doesn't exist
            try:
                info = db_optimizer.execute_query(
                    "PRAGMA table_info(api_keys)", fetch=True
                )
                columns = [r.get("name") for r in (info or []) if isinstance(r, dict)]
                if "allowed_origins" not in columns:
                    db_optimizer.execute_query("""
                        ALTER TABLE api_keys ADD COLUMN allowed_origins TEXT
                    """, fetch=False)
                    logger.info("✅ Added allowed_origins column to api_keys table")
            except Exception as e:
                logger.debug("allowed_origins migration skip or error: %s", e)
            
            logger.info("✅ API key management tables initialized")
            
        except Exception as e:
            logger.error(f"❌ API key table initialization failed: {e}")
    
    def generate_api_key(self, user_id: int, name: str, description: str = None,
                        tenant_id: str = None, scopes: List[str] = None,
                        allowed_origins: List[str] = None,
                        rate_limit_per_minute: int = 60,
                        rate_limit_per_hour: int = 1000,
                        expires_days: int = None) -> Dict[str, Any]:
        """
        Generate a new API key for a user
        
        Returns:
            Dict with 'api_key' (full key, shown only once) and 'key_info' (metadata)
        """
        # Generate secure random key (32 bytes = 64 hex chars)
        raw_key = secrets.token_urlsafe(32)
        key_prefix = raw_key[:8]
        
        # Hash the key for storage (never store raw key)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        # Default scopes
        if scopes is None:
            scopes = ["chatbot:query"]
        
        # Calculate expiration
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        try:
            # Insert API key
            db_optimizer.execute_query("""
                INSERT INTO api_keys (
                    user_id, key_hash, key_prefix, name, description,
                    tenant_id, scopes, allowed_origins, rate_limit_per_minute, rate_limit_per_hour,
                    expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, key_hash, key_prefix, name, description,
                tenant_id, json.dumps(scopes), json.dumps(allowed_origins) if allowed_origins else None,
                rate_limit_per_minute, rate_limit_per_hour, expires_at.isoformat() if expires_at else None
            ), fetch=False)
            
            logger.info(f"✅ Generated API key for user {user_id}: {key_prefix}...")
            
            return {
                "api_key": f"fik_{raw_key}",  # Prefixed for identification
                "key_info": {
                    "key_prefix": key_prefix,
                    "name": name,
                    "scopes": scopes,
                    "tenant_id": tenant_id,
                    "rate_limit_per_minute": rate_limit_per_minute,
                    "rate_limit_per_hour": rate_limit_per_hour,
                    "expires_at": expires_at.isoformat() if expires_at else None
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate API key: {e}")
            raise
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate an API key and return key metadata
        
        Returns:
            Dict with key info if valid, None if invalid
        """
        if not api_key or not api_key.startswith("fik_"):
            return None
        
        # Remove prefix
        raw_key = api_key[4:]  # Remove "fik_" prefix
        
        # Hash the provided key
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        try:
            # Look up key
            result = db_optimizer.execute_query("""
                SELECT id, user_id, key_prefix, name, description, tenant_id,
                       scopes, allowed_origins, rate_limit_per_minute, rate_limit_per_hour,
                       is_active, expires_at, last_used_at
                FROM api_keys
                WHERE key_hash = ? AND is_active = 1
            """, (key_hash,))
            
            if not result:
                return None
            
            key_data = result[0]
            
            # Check expiration
            if key_data.get('expires_at'):
                expires_at = datetime.fromisoformat(key_data['expires_at'])
                if datetime.utcnow() > expires_at:
                    logger.warning(f"API key expired: {key_data.get('key_prefix')}...")
                    return None
            
            # Parse scopes
            import json
            scopes = json.loads(key_data['scopes']) if isinstance(key_data['scopes'], str) else key_data['scopes']
            allowed_origins = None
            if key_data.get('allowed_origins'):
                allowed_origins = json.loads(key_data['allowed_origins']) if isinstance(key_data['allowed_origins'], str) else key_data['allowed_origins']
            
            return {
                "api_key_id": key_data['id'],
                "user_id": key_data['user_id'],
                "key_prefix": key_data['key_prefix'],
                "name": key_data['name'],
                "tenant_id": key_data.get('tenant_id'),
                "scopes": scopes,
                "allowed_origins": allowed_origins,
                "rate_limit_per_minute": key_data['rate_limit_per_minute'],
                "rate_limit_per_hour": key_data['rate_limit_per_hour']
            }
            
        except Exception as e:
            logger.error(f"❌ API key validation failed: {e}")
            return None
    
    def record_usage(self, api_key_id: int, endpoint: str, ip_address: str = None,
                    user_agent: str = None, response_status: int = None,
                    response_time_ms: int = None):
        """Record API key usage for analytics and rate limiting"""
        try:
            db_optimizer.execute_query("""
                INSERT INTO api_key_usage (
                    api_key_id, endpoint, ip_address, user_agent,
                    response_status, response_time_ms
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (api_key_id, endpoint, ip_address, user_agent, response_status, response_time_ms), fetch=False)
            
            # Update last_used_at
            db_optimizer.execute_query("""
                UPDATE api_keys
                SET last_used_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (api_key_id,), fetch=False)
            
        except Exception as e:
            logger.error(f"❌ Failed to record API key usage: {e}")
    
    def check_rate_limit(self, api_key_id: int, limit_type: str = 'minute') -> Dict[str, Any]:
        """
        Check if API key has exceeded rate limit
        
        Returns:
            Dict with 'allowed', 'remaining', 'reset_time'
        """
        try:
            # Get rate limit config
            result = db_optimizer.execute_query("""
                SELECT rate_limit_per_minute, rate_limit_per_hour
                FROM api_keys
                WHERE id = ?
            """, (api_key_id,))
            
            if not result:
                return {"allowed": False, "remaining": 0, "reset_time": None}
            
            limit = result[0][f'rate_limit_per_{limit_type}']
            
            # Count recent requests
            if limit_type == 'minute':
                since = datetime.utcnow() - timedelta(minutes=1)
            else:
                since = datetime.utcnow() - timedelta(hours=1)
            since_str = since.strftime("%Y-%m-%d %H:%M:%S")
            
            count_result = db_optimizer.execute_query("""
                SELECT COUNT(*) as count
                FROM api_key_usage
                WHERE api_key_id = ? AND created_at >= ?
            """, (api_key_id, since_str))
            
            count = count_result[0]['count'] if count_result else 0
            remaining = max(0, limit - count)
            allowed = count < limit
            
            return {
                "allowed": allowed,
                "remaining": remaining,
                "limit": limit,
                "used": count
            }
            
        except Exception as e:
            logger.error(f"❌ Rate limit check failed: {e}")
            # Fail open for availability
            return {"allowed": True, "remaining": 999999, "limit": 999999}
    
    def revoke_api_key(self, api_key_id: int, user_id: int) -> bool:
        """Revoke an API key"""
        try:
            db_optimizer.execute_query("""
                UPDATE api_keys
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            """, (api_key_id, user_id), fetch=False)
            
            logger.info(f"✅ Revoked API key {api_key_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to revoke API key: {e}")
            return False
    
    def list_api_keys(self, user_id: int) -> List[Dict[str, Any]]:
        """List all API keys for a user"""
        try:
            result = db_optimizer.execute_query("""
                SELECT id, key_prefix, name, description, tenant_id, scopes,
                       rate_limit_per_minute, rate_limit_per_hour,
                       is_active, expires_at, last_used_at, created_at
                FROM api_keys
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            
            keys = []
            for row in result:
                import json
                scopes = json.loads(row['scopes']) if isinstance(row['scopes'], str) else row['scopes']
                keys.append({
                    "id": row['id'],
                    "key_prefix": row['key_prefix'],
                    "name": row['name'],
                    "description": row.get('description'),
                    "tenant_id": row.get('tenant_id'),
                    "scopes": scopes,
                    "rate_limit_per_minute": row['rate_limit_per_minute'],
                    "rate_limit_per_hour": row['rate_limit_per_hour'],
                    "is_active": bool(row['is_active']),
                    "expires_at": row.get('expires_at'),
                    "last_used_at": row.get('last_used_at'),
                    "created_at": row['created_at']
                })
            
            return keys
            
        except Exception as e:
            logger.error(f"❌ Failed to list API keys: {e}")
            return []


# Global instance
api_key_manager = APIKeyManager()
