#!/usr/bin/env python3
"""
Redis Session Management for Fikiri Solutions
Replace Flask's in-memory sessions with Redis-backed sessions
"""

import json
import time
import uuid
import logging
from typing import Optional, Dict, Any, List

# Optional Redis integration
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

try:
    from flask import session, request, g
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    session = None
    request = None
    g = None

try:
    from core.minimal_config import get_config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    get_config = None

logger = logging.getLogger(__name__)

class RedisSessionManager:
    """Redis-backed session management for Flask"""
    
    def __init__(self):
        self.config = get_config()
        self.redis_client = None
        self.session_prefix = "fikiri:session:"
        self.session_ttl = 86400  # 24 hours
        self._connect()
    
    def _connect(self):
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using in-memory sessions")
            self.redis_client = None
            return
            
        try:
            # Create Redis client directly
            import os
            redis_url = os.getenv('REDIS_URL')
            if redis_url:
                self.redis_client = redis.from_url(redis_url)
            else:
                self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
            
            if self.redis_client:
                self.redis_client.ping()
                logger.info("✅ Redis session manager connected directly")
        except Exception as e:
            logger.error(f"❌ Redis session connection failed: {e}")
            self.redis_client = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.debug(f"Redis ping failed: {e}")
            return False
    
    def create_session(self, user_id: str, user_data: Dict[str, Any]) -> str:
        """Create new session for user"""
        if not self.is_connected():
            return None
        
        try:
            session_id = str(uuid.uuid4())
            session_key = f"{self.session_prefix}{session_id}"
            
            session_data = {
                'user_id': user_id,
                'user_data': user_data,
                'created_at': time.time(),
                'last_accessed': time.time(),
                'ip_address': request.remote_addr if request else None,
                'user_agent': request.headers.get('User-Agent') if request else None
            }
            
            self.redis_client.setex(session_key, self.session_ttl, json.dumps(session_data))
            logger.info(f"✅ Created session for user {user_id}: {session_id}")
            
            return session_id
            
        except Exception as e:
            logger.error(f"❌ Session creation failed: {e}")
            return None
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        if not self.is_connected() or not session_id:
            return None
        
        try:
            session_key = f"{self.session_prefix}{session_id}"
            session_data = self.redis_client.get(session_key)
            
            if session_data:
                data = json.loads(session_data)
                
                # Update last accessed time
                data['last_accessed'] = time.time()
                self.redis_client.setex(session_key, self.session_ttl, json.dumps(data))
                
                logger.info(f"✅ Retrieved session: {session_id}")
                return data
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Session retrieval failed: {e}")
            return None
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update session data"""
        if not self.is_connected() or not session_id:
            return False
        
        try:
            session_key = f"{self.session_prefix}{session_id}"
            session_data = self.redis_client.get(session_key)
            
            if session_data:
                data = json.loads(session_data)
                data.update(updates)
                data['last_accessed'] = time.time()
                
                self.redis_client.setex(session_key, self.session_ttl, json.dumps(data))
                logger.info(f"✅ Updated session: {session_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Session update failed: {e}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        if not self.is_connected() or not session_id:
            return False
        
        try:
            session_key = f"{self.session_prefix}{session_id}"
            result = self.redis_client.delete(session_key)
            logger.info(f"✅ Deleted session: {session_id}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"❌ Session deletion failed: {e}")
            return False
    
    def extend_session(self, session_id: str, additional_ttl: int = None) -> bool:
        """Extend session TTL"""
        if not self.is_connected() or not session_id:
            return False
        
        try:
            session_key = f"{self.session_prefix}{session_id}"
            ttl = additional_ttl or self.session_ttl
            
            result = self.redis_client.expire(session_key, ttl)
            logger.info(f"✅ Extended session TTL: {session_id}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"❌ Session extension failed: {e}")
            return False
    
    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        if not self.is_connected():
            return []
        
        try:
            pattern = f"{self.session_prefix}*"
            session_keys = self.redis_client.keys(pattern)
            user_sessions = []
            
            for key in session_keys:
                session_data = self.redis_client.get(key)
                if session_data:
                    data = json.loads(session_data)
                    if data.get('user_id') == user_id:
                        session_id = key.replace(self.session_prefix, '')
                        data['session_id'] = session_id
                        user_sessions.append(data)
            
            logger.info(f"✅ Found {len(user_sessions)} sessions for user {user_id}")
            return user_sessions
            
        except Exception as e:
            logger.error(f"❌ User sessions retrieval failed: {e}")
            return []
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (Redis handles this automatically)"""
        # Redis automatically expires keys, but we can count active sessions
        if not self.is_connected():
            return 0
        
        try:
            pattern = f"{self.session_prefix}*"
            active_sessions = len(self.redis_client.keys(pattern))
            logger.info(f"✅ Active sessions: {active_sessions}")
            return active_sessions
            
        except Exception as e:
            logger.error(f"❌ Session cleanup failed: {e}")
            return 0
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        if not self.is_connected():
            return {}
        
        try:
            pattern = f"{self.session_prefix}*"
            session_keys = self.redis_client.keys(pattern)
            
            stats = {
                'total_sessions': len(session_keys),
                'session_prefix': self.session_prefix,
                'session_ttl': self.session_ttl
            }
            
            # Analyze session data
            user_sessions = {}
            for key in session_keys:
                session_data = self.redis_client.get(key)
                if session_data:
                    data = json.loads(session_data)
                    user_id = data.get('user_id')
                    if user_id:
                        user_sessions[user_id] = user_sessions.get(user_id, 0) + 1
            
            stats['unique_users'] = len(user_sessions)
            stats['sessions_per_user'] = sum(user_sessions.values()) / max(1, len(user_sessions))
            
            logger.info(f"✅ Session stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Session stats failed: {e}")
            return {}

# Global session manager
session_manager = RedisSessionManager()

def get_session_manager() -> RedisSessionManager:
    """Get global session manager"""
    return session_manager

# Flask session integration
def init_flask_sessions(app):
    """Initialize Flask with Redis sessions"""
    
    @app.before_request
    def load_session():
        """Load session from Redis before each request"""
        session_id = session.get('session_id')
        if session_id:
            session_data = session_manager.get_session(session_id)
            if session_data:
                g.user_id = session_data.get('user_id')
                g.user_data = session_data.get('user_data', {})
                g.session_data = session_data
            else:
                # Session expired or invalid
                session.pop('session_id', None)
                g.user_id = None
                g.user_data = {}
                g.session_data = {}
        else:
            g.user_id = None
            g.user_data = {}
            g.session_data = {}
    
    @app.after_request
    def save_session(response):
        """Save session to Redis after each request"""
        if hasattr(g, 'session_data') and g.session_data:
            session_id = session.get('session_id')
            if session_id:
                session_manager.update_session(session_id, g.session_data)
        
        return response

# Session helper functions
def create_user_session(user_id: str, user_data: Dict[str, Any]) -> str:
    """Create session for authenticated user"""
    session_id = session_manager.create_session(user_id, user_data)
    if session_id:
        session['session_id'] = session_id
        session.permanent = True
    return session_id

def get_current_user() -> Optional[Dict[str, Any]]:
    """Get current user from session"""
    if hasattr(g, 'user_data') and g.user_data:
        return g.user_data
    return None

def get_current_user_id() -> Optional[str]:
    """Get current user ID from session"""
    if hasattr(g, 'user_id') and g.user_id:
        return g.user_id
    return None

def logout_user():
    """Logout current user"""
    session_id = session.get('session_id')
    if session_id:
        session_manager.delete_session(session_id)
        session.pop('session_id', None)
        session.pop('_permanent', None)

def is_user_logged_in() -> bool:
    """Check if user is logged in"""
    return bool(get_current_user_id())

def require_login(f):
    """Decorator to require user login"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_user_logged_in():
            return {'error': 'Authentication required'}, 401
        return f(*args, **kwargs)
    
    return decorated_function
