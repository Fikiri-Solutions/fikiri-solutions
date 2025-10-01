#!/usr/bin/env python3
"""
JWT Authentication with Refresh Token Rotation
Secure token management with automatic refresh and Redis session persistence
"""

import os
import json
import time
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from functools import wraps

# Optional JWT integration
try:
    import jwt
    from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    jwt = None
    InvalidTokenError = Exception
    ExpiredSignatureError = Exception

# Optional Redis integration
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

class JWTAuthManager:
    """JWT authentication with refresh token rotation and Redis session management"""
    
    def __init__(self):
        self.secret_key = os.getenv('JWT_SECRET_KEY', secrets.token_urlsafe(32))
        self.algorithm = 'HS256'
        self.access_token_expiry = 15 * 60  # 15 minutes
        self.refresh_token_expiry = 7 * 24 * 60 * 60  # 7 days
        self.redis_client = None
        self.session_prefix = "fikiri:jwt:session:"
        self.refresh_prefix = "fikiri:jwt:refresh:"
        self._connect_redis()
        self._initialize_tables()
    
    def _connect_redis(self):
        """Connect to Redis for session storage"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using in-memory sessions")
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
            logger.info("✅ JWT Redis connection established")
            
        except Exception as e:
            logger.error(f"❌ JWT Redis connection failed: {e}")
            self.redis_client = None
    
    def _initialize_tables(self):
        """Initialize database tables for JWT management"""
        try:
            # Create refresh tokens table
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    expires_at DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_revoked BOOLEAN DEFAULT FALSE,
                    device_info TEXT,
                    ip_address TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """, fetch=False)
            
            # Create index for faster lookups
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id 
                ON refresh_tokens (user_id)
            """, fetch=False)
            
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash 
                ON refresh_tokens (token_hash)
            """, fetch=False)
            
            logger.info("✅ JWT tables initialized")
            
        except Exception as e:
            logger.error(f"❌ JWT table initialization failed: {e}")
    
    def generate_tokens(self, user_id: int, user_data: Dict[str, Any], 
                       device_info: str = None, ip_address: str = None) -> Dict[str, Any]:
        """Generate access and refresh tokens"""
        if not JWT_AVAILABLE:
            raise Exception("JWT library not available")
        
        try:
            current_time = datetime.utcnow()
            
            # Access token payload
            access_payload = {
                'user_id': user_id,
                'email': user_data.get('email'),
                'role': user_data.get('role', 'user'),
                'type': 'access',
                'iat': current_time,
                'exp': current_time + timedelta(seconds=self.access_token_expiry)
            }
            
            # Generate access token
            access_token = jwt.encode(access_payload, self.secret_key, algorithm=self.algorithm)
            
            # Generate refresh token
            refresh_token = secrets.token_urlsafe(32)
            refresh_token_hash = self._hash_token(refresh_token)
            
            # Store refresh token in database
            refresh_expires = current_time + timedelta(seconds=self.refresh_token_expiry)
            db_optimizer.execute_query("""
                INSERT INTO refresh_tokens 
                (user_id, token_hash, expires_at, device_info, ip_address)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id, 
                refresh_token_hash, 
                refresh_expires.isoformat(),
                device_info,
                ip_address
            ), fetch=False)
            
            # Store session in Redis if available
            if self.redis_client:
                session_data = {
                    'user_id': user_id,
                    'user_data': user_data,
                    'access_token': access_token,
                    'created_at': current_time.isoformat(),
                    'last_accessed': current_time.isoformat()
                }
                
                session_key = f"{self.session_prefix}{user_id}"
                self.redis_client.setex(
                    session_key, 
                    self.access_token_expiry, 
                    json.dumps(session_data)
                )
            
            logger.info(f"✅ Generated tokens for user {user_id}")
            
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_in': self.access_token_expiry,
                'token_type': 'Bearer'
            }
            
        except Exception as e:
            logger.error(f"❌ Token generation failed: {e}")
            raise
    
    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode access token"""
        if not JWT_AVAILABLE:
            return None
        
        try:
            # Remove Bearer prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Verify token type
            if payload.get('type') != 'access':
                return None
            
            # Check if user still exists and is active
            user_data = db_optimizer.execute_query(
                "SELECT * FROM users WHERE id = ? AND is_active = 1",
                (payload['user_id'],)
            )
            
            if not user_data:
                return None
            
            # Update Redis session if available
            if self.redis_client:
                session_key = f"{self.session_prefix}{payload['user_id']}"
                session_data = self.redis_client.get(session_key)
                if session_data:
                    data = json.loads(session_data)
                    data['last_accessed'] = datetime.utcnow().isoformat()
                    self.redis_client.setex(
                        session_key, 
                        self.access_token_expiry, 
                        json.dumps(data)
                    )
            
            return payload
            
        except ExpiredSignatureError:
            logger.warning("Access token expired")
            return None
        except InvalidTokenError:
            logger.warning("Invalid access token")
            return None
        except Exception as e:
            logger.error(f"❌ Token verification failed: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh access token using refresh token"""
        if not JWT_AVAILABLE:
            return None
        
        try:
            # Hash the refresh token
            token_hash = self._hash_token(refresh_token)
            
            # Find refresh token in database
            token_data = db_optimizer.execute_query("""
                SELECT rt.*, u.* FROM refresh_tokens rt
                JOIN users u ON rt.user_id = u.id
                WHERE rt.token_hash = ? AND rt.is_revoked = FALSE 
                AND rt.expires_at > datetime('now') AND u.is_active = 1
            """, (token_hash,))
            
            if not token_data:
                logger.warning("Invalid or expired refresh token")
                return None
            
            token_record = token_data[0]
            user_id = token_record['user_id']
            
            # Get user data
            user_data = {
                'email': token_record['email'],
                'name': token_record['name'],
                'role': token_record['role']
            }
            
            # Revoke old refresh token
            db_optimizer.execute_query("""
                UPDATE refresh_tokens SET is_revoked = TRUE 
                WHERE token_hash = ?
            """, (token_hash,), fetch=False)
            
            # Generate new tokens
            new_tokens = self.generate_tokens(
                user_id, 
                user_data, 
                token_record.get('device_info'),
                token_record.get('ip_address')
            )
            
            logger.info(f"✅ Refreshed tokens for user {user_id}")
            return new_tokens
            
        except Exception as e:
            logger.error(f"❌ Token refresh failed: {e}")
            return None
    
    def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Revoke a refresh token"""
        try:
            token_hash = self._hash_token(refresh_token)
            
            result = db_optimizer.execute_query("""
                UPDATE refresh_tokens SET is_revoked = TRUE 
                WHERE token_hash = ?
            """, (token_hash,), fetch=False)
            
            logger.info("✅ Refresh token revoked")
            return True
            
        except Exception as e:
            logger.error(f"❌ Token revocation failed: {e}")
            return False
    
    def revoke_all_user_tokens(self, user_id: int) -> bool:
        """Revoke all refresh tokens for a user"""
        try:
            # Revoke all database tokens
            db_optimizer.execute_query("""
                UPDATE refresh_tokens SET is_revoked = TRUE 
                WHERE user_id = ?
            """, (user_id,), fetch=False)
            
            # Clear Redis session
            if self.redis_client:
                session_key = f"{self.session_prefix}{user_id}"
                self.redis_client.delete(session_key)
            
            logger.info(f"✅ All tokens revoked for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Token revocation failed: {e}")
            return False
    
    def get_user_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user session from Redis"""
        if not self.redis_client:
            return None
        
        try:
            session_key = f"{self.session_prefix}{user_id}"
            session_data = self.redis_client.get(session_key)
            
            if session_data:
                return json.loads(session_data)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Session retrieval failed: {e}")
            return None
    
    def _hash_token(self, token: str) -> str:
        """Hash token for secure storage"""
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()
    
    def cleanup_expired_tokens(self):
        """Clean up expired refresh tokens"""
        try:
            db_optimizer.execute_query("""
                DELETE FROM refresh_tokens 
                WHERE expires_at < datetime('now') OR is_revoked = TRUE
            """, fetch=False)
            
            logger.info("✅ Expired tokens cleaned up")
            
        except Exception as e:
            logger.error(f"❌ Token cleanup failed: {e}")

# Global JWT manager
jwt_auth_manager = JWTAuthManager()

# Decorator for JWT authentication
def jwt_required(f):
    """Decorator to require JWT authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, jsonify
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'error': 'Authorization header missing or invalid',
                'error_code': 'MISSING_AUTH_HEADER'
            }), 401
        
        # Verify token
        token = auth_header.split(' ')[1]
        payload = jwt_auth_manager.verify_access_token(token)
        
        if not payload:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired token',
                'error_code': 'INVALID_TOKEN'
            }), 401
        
        # Add user info to request context
        request.current_user = payload
        
        return f(*args, **kwargs)
    
    return decorated_function

# Helper function to get current user
def get_current_user():
    """Get current user from request context"""
    from flask import request
    return getattr(request, 'current_user', None)
