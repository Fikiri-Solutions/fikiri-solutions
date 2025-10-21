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
        # Fixed secret key with proper warning
        self.secret_key = os.getenv('JWT_SECRET_KEY')
        if not self.secret_key:
            self.secret_key = secrets.token_urlsafe(32)
            logger.warning("⚠️ JWT_SECRET_KEY not set — generating ephemeral key (tokens will reset on restart)")
        
        self.algorithm = 'HS256'
        
        # Configurable token expiries via environment variables
        self.access_token_expiry = int(os.getenv("JWT_ACCESS_EXPIRY", 30 * 60))  # 30 minutes default (extended from 15)
        self.refresh_token_expiry = int(os.getenv("JWT_REFRESH_EXPIRY", 7 * 24 * 60 * 60))  # 7 days default
        
        self.redis_client = None
        self.session_prefix = "fikiri:jwt:session:"
        self.refresh_prefix = "fikiri:jwt:refresh:"
        self.blacklist_prefix = "fikiri:jwt:blacklist:"
        
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
        """Initialize database tables for JWT management with DB integrity"""
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
                    device_id TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """, fetch=False)
            
            # Add device_id column if it doesn't exist (schema migration)
            try:
                # Check if device_id column already exists
                existing_columns = db_optimizer.execute_query("""
                    PRAGMA table_info(refresh_tokens)
                """)
                column_names = [col[1] for col in existing_columns] if existing_columns else []
                
                if "device_id" not in column_names:
                    db_optimizer.execute_query("""
                        ALTER TABLE refresh_tokens ADD COLUMN device_id TEXT
                    """, fetch=False)
                    logger.info("✅ Added device_id column to refresh_tokens")
                else:
                    logger.info("ℹ️ device_id column already exists in refresh_tokens")
            except Exception as e:
                # Column already exists, ignore
                pass
            
            # Create indexes for faster lookups
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id 
                ON refresh_tokens (user_id)
            """, fetch=False)
            
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash 
                ON refresh_tokens (token_hash)
            """, fetch=False)
            
            # Add expiry index for cleanup automation
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires 
                ON refresh_tokens (expires_at)
            """, fetch=False)
            
            logger.info("✅ JWT tables initialized")
            
        except Exception as e:
            logger.error(f"❌ JWT table initialization failed: {e}")
    
    def generate_tokens(self, user_id: int, user_data: Dict[str, Any], 
                       device_info: str = None, ip_address: str = None) -> Dict[str, Any]:
        """Generate access and refresh tokens with multi-device support"""
        if not JWT_AVAILABLE:
            raise Exception("JWT library not available")
        
        try:
            current_time = datetime.now()
            
            # Generate unique device ID for multi-device support
            device_id = secrets.token_hex(4)
            
            # Access token payload with Unix timestamps
            access_payload = {
                'user_id': user_id,
                'email': user_data.get('email'),
                'role': user_data.get('role', 'user'),
                'type': 'access',
                'jti': secrets.token_urlsafe(16),  # JWT ID for blacklisting
                'iat': int(current_time.timestamp()),
                'exp': int((current_time + timedelta(seconds=self.access_token_expiry)).timestamp())
            }
            
            # Generate access token
            access_token = jwt.encode(access_payload, self.secret_key, algorithm=self.algorithm)
            
            # Generate refresh token
            refresh_token = secrets.token_urlsafe(32)
            refresh_token_hash = self._hash_token(refresh_token)
            
            # Store refresh token in database with device ID
            refresh_expires = current_time + timedelta(seconds=self.refresh_token_expiry)
            db_optimizer.execute_query("""
                INSERT INTO refresh_tokens 
                (user_id, token_hash, expires_at, device_info, ip_address, device_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id, 
                refresh_token_hash, 
                refresh_expires.isoformat(),
                device_info,
                ip_address,
                device_id
            ), fetch=False)
            
            # Store session in Redis with device-specific key
            if self.redis_client:
                session_data = {
                    'user_id': user_id,
                    'user_data': user_data,
                    'access_token': access_token,
                    'device_id': device_id,
                    'created_at': current_time.isoformat(),
                    'last_accessed': current_time.isoformat()
                }
                
                session_key = f"{self.session_prefix}{user_id}:{device_id}"
                self.redis_client.setex(
                    session_key, 
                    self.access_token_expiry, 
                    json.dumps(session_data)
                )
            
            logger.info(f"✅ Generated tokens for user {user_id} (device: {device_id})")
            
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_in': self.access_token_expiry,
                'token_type': 'Bearer',
                'device_id': device_id
            }
            
        except Exception as e:
            logger.error(f"❌ Token generation failed: {e}")
            raise
    
    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode access token with blacklist checking"""
        if not JWT_AVAILABLE:
            return {"error": "jwt_unavailable"}
        
        try:
            # Remove Bearer prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token is blacklisted
            jti = payload.get('jti')
            if jti and self.is_token_blacklisted(jti):
                logger.warning("Token is blacklisted")
                return {"error": "blacklisted"}
            
            # Verify token type
            if payload.get('type') != 'access':
                return {"error": "invalid_type"}
            
            # Check if user still exists and is active
            user_data = db_optimizer.execute_query(
                "SELECT * FROM users WHERE id = ? AND is_active = 1",
                (payload['user_id'],)
            )
            
            if not user_data:
                return {"error": "user_inactive"}
            
            # Update Redis session if available
            if self.redis_client:
                device_id = payload.get('device_id', 'default')
                session_key = f"{self.session_prefix}{payload['user_id']}:{device_id}"
                session_data = self.redis_client.get(session_key)
                if session_data:
                    data = json.loads(session_data)
                    data['last_accessed'] = datetime.now().isoformat()
                    self.redis_client.setex(
                        session_key, 
                        self.access_token_expiry, 
                        json.dumps(data)
                    )
            
            return payload
            
        except ExpiredSignatureError:
            logger.warning("Access token expired")
            return {"error": "expired"}
        except InvalidTokenError:
            logger.warning("Invalid access token")
            return {"error": "invalid"}
        except Exception as e:
            logger.error(f"❌ Token verification failed: {e}")
            return {"error": "verification_failed"}
    
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
            
            # Clear Redis sessions for all devices
            if self.redis_client:
                pattern = f"{self.session_prefix}{user_id}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            
            logger.info(f"✅ All tokens revoked for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Token revocation failed: {e}")
            return False
    
    def get_user_session(self, user_id: int, device_id: str = None) -> Optional[Dict[str, Any]]:
        """Get user session from Redis with device support"""
        if not self.redis_client:
            return None
        
        try:
            if device_id:
                session_key = f"{self.session_prefix}{user_id}:{device_id}"
            else:
                # Get any active session for the user
                pattern = f"{self.session_prefix}{user_id}:*"
                keys = self.redis_client.keys(pattern)
                if not keys:
                    return None
                session_key = keys[0]  # Use first available session
            
            session_data = self.redis_client.get(session_key)
            
            if session_data:
                return json.loads(session_data)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Session retrieval failed: {e}")
            return None
    
    def is_token_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted via Redis"""
        if not self.redis_client:
            return False
        
        try:
            blacklist_key = f"{self.blacklist_prefix}{jti}"
            return self.redis_client.exists(blacklist_key)
        except Exception as e:
            logger.error(f"❌ Blacklist check failed: {e}")
            return False
    
    def blacklist_token(self, jti: str, expires_at: datetime = None) -> bool:
        """Add token to blacklist"""
        if not self.redis_client:
            return False
        
        try:
            blacklist_key = f"{self.blacklist_prefix}{jti}"
            
            if expires_at:
                # Set expiration for blacklist entry
                ttl = int((expires_at - datetime.utcnow()).total_seconds())
                if ttl > 0:
                    self.redis_client.setex(blacklist_key, ttl, "blacklisted")
                else:
                    return True  # Token already expired
            else:
                # Set with default TTL (access token expiry)
                self.redis_client.setex(blacklist_key, self.access_token_expiry, "blacklisted")
            
            logger.info(f"✅ Token blacklisted: {jti}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Token blacklisting failed: {e}")
            return False
    
    def logout_user(self, access_token: str) -> bool:
        """Logout user by blacklisting access token"""
        try:
            # Decode token to get JTI
            if access_token.startswith('Bearer '):
                access_token = access_token[7:]
            
            payload = jwt.decode(access_token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            jti = payload.get('jti')
            
            if jti:
                # Blacklist the access token
                expires_at = datetime.fromtimestamp(payload.get('exp', 0))
                return self.blacklist_token(jti, expires_at)
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Logout failed: {e}")
            return False
    
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

# Global JWT manager - lazy loaded
jwt_auth_manager = None

def get_jwt_manager():
    """Get or create JWT manager instance"""
    global jwt_auth_manager
    if jwt_auth_manager is None:
        jwt_auth_manager = JWTAuthManager()
    return jwt_auth_manager

# Decorator for JWT authentication with rate limiting support
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
        payload = get_jwt_manager().verify_access_token(token)
        
        if isinstance(payload, dict) and 'error' in payload:
            error_code = payload['error']
            if error_code == 'expired':
                return jsonify({
                    'success': False,
                    'error': 'Token expired',
                    'error_code': 'TOKEN_EXPIRED'
                }), 401
            elif error_code == 'blacklisted':
                return jsonify({
                    'success': False,
                    'error': 'Token has been revoked',
                    'error_code': 'TOKEN_REVOKED'
                }), 401
            elif error_code == 'user_inactive':
                return jsonify({
                    'success': False,
                    'error': 'User account is inactive',
                    'error_code': 'USER_INACTIVE'
                }), 401
            else:
                return jsonify({
                    'success': False,
                    'error': 'Invalid token',
                    'error_code': 'INVALID_TOKEN'
                }), 401
        
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