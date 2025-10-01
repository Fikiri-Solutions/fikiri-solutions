#!/usr/bin/env python3
"""
Secure Session Management with Redis Persistence
Enhanced session handling with httpOnly cookies, SameSite protection, and Redis persistence
"""

import os
import json
import time
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from functools import wraps

# Optional Redis integration
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

try:
    from flask import session, request, g, make_response, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    session = None
    request = None
    g = None
    make_response = None
    jsonify = None

from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

class SecureSessionManager:
    """Secure session management with Redis persistence and cookie security"""
    
    def __init__(self):
        self.redis_client = None
        self.session_prefix = "fikiri:secure:session:"
        self.session_ttl = 24 * 60 * 60  # 24 hours
        self.cookie_name = "fikiri_session"
        self.cookie_secure = os.getenv('FLASK_ENV') == 'production'
        self.cookie_httponly = True
        self.cookie_samesite = 'Strict'
        self.cookie_domain = os.getenv('SESSION_COOKIE_DOMAIN')
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
            logger.info("✅ Secure session Redis connection established")
            
        except Exception as e:
            logger.error(f"❌ Secure session Redis connection failed: {e}")
            self.redis_client = None
    
    def _initialize_tables(self):
        """Initialize database tables for session management"""
        try:
            # Create secure sessions table for tracking
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS secure_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL UNIQUE,
                    user_id INTEGER,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    metadata TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """, fetch=False)
            
            # Create indexes
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_secure_sessions_user_id 
                ON secure_sessions (user_id)
            """, fetch=False)
            
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_secure_sessions_session_id 
                ON secure_sessions (session_id)
            """, fetch=False)
            
            logger.info("✅ Secure session tables initialized")
            
        except Exception as e:
            logger.error(f"❌ Secure session table initialization failed: {e}")
    
    def create_session(self, user_id: int, user_data: Dict[str, Any], 
                      ip_address: str = None, user_agent: str = None) -> Tuple[str, Dict[str, Any]]:
        """Create a new secure session"""
        try:
            # Generate secure session ID
            session_id = secrets.token_urlsafe(32)
            current_time = datetime.utcnow()
            expires_at = current_time + timedelta(seconds=self.session_ttl)
            
            # Prepare session data
            session_data = {
                'session_id': session_id,
                'user_id': user_id,
                'user_data': user_data,
                'ip_address': ip_address or (request.remote_addr if request else None),
                'user_agent': user_agent or (request.headers.get('User-Agent') if request else None),
                'created_at': current_time.isoformat(),
                'last_accessed': current_time.isoformat(),
                'expires_at': expires_at.isoformat(),
                'is_active': True
            }
            
            # Store in Redis if available
            if self.redis_client:
                session_key = f"{self.session_prefix}{session_id}"
                self.redis_client.setex(
                    session_key, 
                    self.session_ttl, 
                    json.dumps(session_data)
                )
            
            # Store in database for tracking
            db_optimizer.execute_query("""
                INSERT INTO secure_sessions 
                (session_id, user_id, ip_address, user_agent, expires_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                user_id,
                session_data['ip_address'],
                session_data['user_agent'],
                expires_at.isoformat(),
                json.dumps({'user_data': user_data})
            ), fetch=False)
            
            # Create secure cookie
            cookie_data = self._create_secure_cookie(session_id)
            
            logger.info(f"✅ Created secure session for user {user_id}: {session_id}")
            
            return session_id, cookie_data
            
        except Exception as e:
            logger.error(f"❌ Session creation failed: {e}")
            raise
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by session ID"""
        if not session_id:
            return None
        
        try:
            # Try Redis first
            if self.redis_client:
                session_key = f"{self.session_prefix}{session_id}"
                session_data = self.redis_client.get(session_key)
                
                if session_data:
                    data = json.loads(session_data)
                    
                    # Update last accessed time
                    data['last_accessed'] = datetime.utcnow().isoformat()
                    self.redis_client.setex(
                        session_key, 
                        self.session_ttl, 
                        json.dumps(data)
                    )
                    
                    # Update database
                    self._update_session_access(session_id)
                    
                    return data
            
            # Fallback to database
            db_data = db_optimizer.execute_query("""
                SELECT * FROM secure_sessions 
                WHERE session_id = ? AND is_active = TRUE 
                AND expires_at > datetime('now')
            """, (session_id,))
            
            if db_data:
                session_record = db_data[0]
                metadata = json.loads(session_record.get('metadata', '{}'))
                
                session_data = {
                    'session_id': session_record['session_id'],
                    'user_id': session_record['user_id'],
                    'user_data': metadata.get('user_data', {}),
                    'ip_address': session_record['ip_address'],
                    'user_agent': session_record['user_agent'],
                    'created_at': session_record['created_at'],
                    'last_accessed': session_record['last_accessed'],
                    'expires_at': session_record['expires_at'],
                    'is_active': session_record['is_active']
                }
                
                # Update last accessed
                self._update_session_access(session_id)
                
                return session_data
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Session retrieval failed: {e}")
            return None
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update session data"""
        try:
            # Update Redis if available
            if self.redis_client:
                session_key = f"{self.session_prefix}{session_id}"
                session_data = self.redis_client.get(session_key)
                
                if session_data:
                    data = json.loads(session_data)
                    data.update(updates)
                    data['last_accessed'] = datetime.utcnow().isoformat()
                    
                    self.redis_client.setex(
                        session_key, 
                        self.session_ttl, 
                        json.dumps(data)
                    )
            
            # Update database metadata
            if 'user_data' in updates:
                db_optimizer.execute_query("""
                    UPDATE secure_sessions 
                    SET metadata = ?, last_accessed = datetime('now')
                    WHERE session_id = ?
                """, (
                    json.dumps({'user_data': updates['user_data']}),
                    session_id
                ), fetch=False)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Session update failed: {e}")
            return False
    
    def revoke_session(self, session_id: str) -> bool:
        """Revoke a session"""
        try:
            # Remove from Redis
            if self.redis_client:
                session_key = f"{self.session_prefix}{session_id}"
                self.redis_client.delete(session_key)
            
            # Mark as inactive in database
            db_optimizer.execute_query("""
                UPDATE secure_sessions 
                SET is_active = FALSE 
                WHERE session_id = ?
            """, (session_id,), fetch=False)
            
            logger.info(f"✅ Session revoked: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Session revocation failed: {e}")
            return False
    
    def revoke_all_user_sessions(self, user_id: int) -> bool:
        """Revoke all sessions for a user"""
        try:
            # Get all active sessions for user
            sessions = db_optimizer.execute_query("""
                SELECT session_id FROM secure_sessions 
                WHERE user_id = ? AND is_active = TRUE
            """, (user_id,))
            
            # Revoke each session
            for session_record in sessions:
                session_id = session_record['session_id']
                
                # Remove from Redis
                if self.redis_client:
                    session_key = f"{self.session_prefix}{session_id}"
                    self.redis_client.delete(session_key)
            
            # Mark all as inactive in database
            db_optimizer.execute_query("""
                UPDATE secure_sessions 
                SET is_active = FALSE 
                WHERE user_id = ?
            """, (user_id,), fetch=False)
            
            logger.info(f"✅ All sessions revoked for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ User session revocation failed: {e}")
            return False
    
    def _create_secure_cookie(self, session_id: str) -> Dict[str, Any]:
        """Create secure cookie configuration"""
        return {
            'key': self.cookie_name,
            'value': session_id,
            'max_age': self.session_ttl,
            'secure': self.cookie_secure,
            'httponly': self.cookie_httponly,
            'samesite': self.cookie_samesite,
            'domain': self.cookie_domain
        }
    
    def _update_session_access(self, session_id: str):
        """Update session last accessed time in database"""
        try:
            db_optimizer.execute_query("""
                UPDATE secure_sessions 
                SET last_accessed = datetime('now')
                WHERE session_id = ?
            """, (session_id,), fetch=False)
        except Exception as e:
            logger.error(f"❌ Session access update failed: {e}")
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        try:
            # Clean Redis
            if self.redis_client:
                # Redis TTL handles expiration automatically
                pass
            
            # Clean database
            db_optimizer.execute_query("""
                UPDATE secure_sessions 
                SET is_active = FALSE 
                WHERE expires_at < datetime('now')
            """, fetch=False)
            
            logger.info("✅ Expired sessions cleaned up")
            
        except Exception as e:
            logger.error(f"❌ Session cleanup failed: {e}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        try:
            stats = db_optimizer.execute_query("""
                SELECT 
                    COUNT(*) as total_sessions,
                    COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_sessions,
                    COUNT(CASE WHEN expires_at > datetime('now') THEN 1 END) as valid_sessions
                FROM secure_sessions
            """)
            
            if stats:
                return stats[0]
            
            return {}
            
        except Exception as e:
            logger.error(f"❌ Session stats failed: {e}")
            return {}

# Global session manager
secure_session_manager = SecureSessionManager()

# Flask integration
def init_secure_sessions(app):
    """Initialize Flask with secure session management"""
    
    @app.before_request
    def load_secure_session():
        """Load session from secure cookie before each request"""
        if not FLASK_AVAILABLE:
            return
        
        session_id = None
        
        # Get session ID from cookie
        if request.cookies.get(secure_session_manager.cookie_name):
            session_id = request.cookies.get(secure_session_manager.cookie_name)
        
        # Get session ID from Authorization header (for API calls)
        elif request.headers.get('Authorization'):
            auth_header = request.headers.get('Authorization')
            if auth_header.startswith('Bearer '):
                # This is for JWT tokens, not session tokens
                pass
        
        if session_id:
            session_data = secure_session_manager.get_session(session_id)
            if session_data:
                g.session_id = session_id
                g.user_id = session_data.get('user_id')
                g.user_data = session_data.get('user_data', {})
                g.session_data = session_data
            else:
                # Session expired or invalid
                g.session_id = None
                g.user_id = None
                g.user_data = {}
                g.session_data = {}
        else:
            g.session_id = None
            g.user_id = None
            g.user_data = {}
            g.session_data = {}
    
    @app.after_request
    def save_secure_session(response):
        """Save session after each request"""
        if not FLASK_AVAILABLE:
            return response
        
        # Session updates are handled in real-time
        return response

# Helper functions
def create_secure_session(user_id: int, user_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Create a new secure session"""
    return secure_session_manager.create_session(
        user_id, 
        user_data,
        request.remote_addr if request else None,
        request.headers.get('User-Agent') if request else None
    )

def get_current_session() -> Optional[Dict[str, Any]]:
    """Get current session from Flask context"""
    if not FLASK_AVAILABLE:
        return None
    
    return getattr(g, 'session_data', None)

def get_current_user_id() -> Optional[int]:
    """Get current user ID from session"""
    if not FLASK_AVAILABLE:
        return None
    
    return getattr(g, 'user_id', None)

def require_session(f):
    """Decorator to require valid session"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not FLASK_AVAILABLE:
            return jsonify({'error': 'Flask not available'}), 500
        
        session_data = get_current_session()
        if not session_data:
            return jsonify({
                'success': False,
                'error': 'Session required',
                'error_code': 'SESSION_REQUIRED'
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function
