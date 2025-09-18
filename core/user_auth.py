"""
Enhanced User Authentication System
Handles user registration, login, password hashing, and session management
"""

import hashlib
import secrets
import time
import json
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from core.database_optimization import db_optimizer

logger = logging.getLogger(__name__)

@dataclass
class UserProfile:
    """User profile data structure"""
    id: int
    email: str
    name: str
    role: str
    business_name: Optional[str]
    business_email: Optional[str]
    industry: Optional[str]
    team_size: Optional[str]
    is_active: bool
    email_verified: bool
    created_at: datetime
    onboarding_completed: bool
    onboarding_step: int
    metadata: Dict[str, Any]

class UserAuthManager:
    """Enhanced user authentication and management"""
    
    def __init__(self):
        self.salt_length = 32
        self.session_duration = 24 * 60 * 60  # 24 hours
        self.max_login_attempts = 5
        self.lockout_duration = 15 * 60  # 15 minutes
    
    def _hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """Hash password with salt using PBKDF2"""
        if salt is None:
            salt = secrets.token_hex(self.salt_length)
        
        # Use PBKDF2 with SHA-256
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 100,000 iterations
        )
        
        return password_hash.hex(), salt
    
    def _verify_password(self, password: str, stored_hash: str, salt: str) -> bool:
        """Verify password against stored hash"""
        password_hash, _ = self._hash_password(password, salt)
        return password_hash == stored_hash
    
    def create_user(self, email: str, password: str, name: str, 
                   business_name: str = None, business_email: str = None,
                   industry: str = None, team_size: str = None) -> Dict[str, Any]:
        """Create a new user account"""
        try:
            # Check if user already exists
            existing_user = db_optimizer.execute_query(
                "SELECT id FROM users WHERE email = ?",
                (email,)
            )
            
            if existing_user:
                return {
                    'success': False,
                    'error': 'User with this email already exists',
                    'error_code': 'USER_EXISTS'
                }
            
            # Hash password
            password_hash, salt = self._hash_password(password)
            
            # Create user record
            user_id = db_optimizer.execute_query(
                """INSERT INTO users 
                   (email, name, password_hash, business_name, business_email, 
                    industry, team_size, metadata) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (email, name, password_hash, business_name, business_email,
                 industry, team_size, json.dumps({'salt': salt})),
                fetch=False
            )
            
            # Get the created user
            user_data = db_optimizer.execute_query(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            )[0]
            
            logger.info(f"User created successfully: {email}")
            
            return {
                'success': True,
                'user': self._format_user_profile(user_data),
                'message': 'User account created successfully'
            }
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return {
                'success': False,
                'error': 'Failed to create user account',
                'error_code': 'CREATE_USER_ERROR'
            }
    
    def authenticate_user(self, email: str, password: str, 
                         ip_address: str = None, user_agent: str = None) -> Dict[str, Any]:
        """Authenticate user login"""
        try:
            # Get user data
            user_data = db_optimizer.execute_query(
                "SELECT * FROM users WHERE email = ? AND is_active = 1",
                (email,)
            )
            
            if not user_data:
                return {
                    'success': False,
                    'error': 'Invalid email or password',
                    'error_code': 'INVALID_CREDENTIALS'
                }
            
            user = user_data[0]
            metadata = json.loads(user['metadata'] or '{}')
            salt = metadata.get('salt', '')
            
            # Verify password
            if not self._verify_password(password, user['password_hash'], salt):
                return {
                    'success': False,
                    'error': 'Invalid email or password',
                    'error_code': 'INVALID_CREDENTIALS'
                }
            
            # Create session
            session_result = self._create_session(
                user['id'], ip_address, user_agent
            )
            
            # Update last login
            db_optimizer.execute_query(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (user['id'],),
                fetch=False
            )
            
            logger.info(f"User authenticated successfully: {email}")
            
            return {
                'success': True,
                'user': self._format_user_profile(user),
                'session': session_result,
                'message': 'Login successful'
            }
            
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return {
                'success': False,
                'error': 'Authentication failed',
                'error_code': 'AUTH_ERROR'
            }
    
    def _create_session(self, user_id: int, ip_address: str = None, 
                       user_agent: str = None) -> Dict[str, Any]:
        """Create a new user session"""
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(seconds=self.session_duration)
        
        # Store session in database
        db_optimizer.execute_query(
            """INSERT INTO user_sessions 
               (user_id, session_id, ip_address, user_agent, expires_at) 
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, session_id, ip_address, user_agent, expires_at.isoformat()),
            fetch=False
        )
        
        return {
            'session_id': session_id,
            'expires_at': expires_at.isoformat(),
            'duration': self.session_duration
        }
    
    def validate_session(self, session_id: str) -> Optional[UserProfile]:
        """Validate session and return user profile"""
        try:
            session_data = db_optimizer.execute_query(
                """SELECT s.*, u.* FROM user_sessions s
                   JOIN users u ON s.user_id = u.id
                   WHERE s.session_id = ? AND s.is_valid = 1 
                   AND s.expires_at > datetime('now')""",
                (session_id,)
            )
            
            if not session_data:
                return None
            
            session = session_data[0]
            return self._format_user_profile(session)
            
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return None
    
    def revoke_session(self, session_id: str) -> bool:
        """Revoke a user session"""
        try:
            db_optimizer.execute_query(
                "UPDATE user_sessions SET is_valid = 0 WHERE session_id = ?",
                (session_id,),
                fetch=False
            )
            return True
        except Exception as e:
            logger.error(f"Error revoking session: {e}")
            return False
    
    def revoke_all_user_sessions(self, user_id: int) -> bool:
        """Revoke all sessions for a user"""
        try:
            db_optimizer.execute_query(
                "UPDATE user_sessions SET is_valid = 0 WHERE user_id = ?",
                (user_id,),
                fetch=False
            )
            return True
        except Exception as e:
            logger.error(f"Error revoking user sessions: {e}")
            return False
    
    def update_user_profile(self, user_id: int, **updates) -> Dict[str, Any]:
        """Update user profile information"""
        try:
            # Build update query dynamically
            update_fields = []
            update_values = []
            
            allowed_fields = [
                'name', 'business_name', 'business_email', 'industry', 
                'team_size', 'onboarding_completed', 'onboarding_step'
            ]
            
            for field, value in updates.items():
                if field in allowed_fields:
                    update_fields.append(f"{field} = ?")
                    update_values.append(value)
            
            if not update_fields:
                return {
                    'success': False,
                    'error': 'No valid fields to update',
                    'error_code': 'NO_UPDATES'
                }
            
            update_values.append(user_id)
            
            query = f"UPDATE users SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            
            db_optimizer.execute_query(query, tuple(update_values), fetch=False)
            
            # Get updated user data
            user_data = db_optimizer.execute_query(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            )[0]
            
            return {
                'success': True,
                'user': self._format_user_profile(user_data),
                'message': 'Profile updated successfully'
            }
            
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            return {
                'success': False,
                'error': 'Failed to update profile',
                'error_code': 'UPDATE_ERROR'
            }
    
    def change_password(self, user_id: int, current_password: str, 
                       new_password: str) -> Dict[str, Any]:
        """Change user password"""
        try:
            # Get current user data
            user_data = db_optimizer.execute_query(
                "SELECT password_hash, metadata FROM users WHERE id = ?",
                (user_id,)
            )[0]
            
            metadata = json.loads(user_data['metadata'] or '{}')
            salt = metadata.get('salt', '')
            
            # Verify current password
            if not self._verify_password(current_password, user_data['password_hash'], salt):
                return {
                    'success': False,
                    'error': 'Current password is incorrect',
                    'error_code': 'INVALID_CURRENT_PASSWORD'
                }
            
            # Hash new password
            new_password_hash, new_salt = self._hash_password(new_password)
            
            # Update password and salt
            metadata['salt'] = new_salt
            db_optimizer.execute_query(
                "UPDATE users SET password_hash = ?, metadata = ? WHERE id = ?",
                (new_password_hash, json.dumps(metadata), user_id),
                fetch=False
            )
            
            # Revoke all existing sessions
            self.revoke_all_user_sessions(user_id)
            
            logger.info(f"Password changed for user {user_id}")
            
            return {
                'success': True,
                'message': 'Password changed successfully'
            }
            
        except Exception as e:
            logger.error(f"Error changing password: {e}")
            return {
                'success': False,
                'error': 'Failed to change password',
                'error_code': 'PASSWORD_CHANGE_ERROR'
            }
    
    def _format_user_profile(self, user_data: Dict[str, Any]) -> UserProfile:
        """Format user data into UserProfile object"""
        metadata = json.loads(user_data.get('metadata', '{}'))
        
        return UserProfile(
            id=user_data['id'],
            email=user_data['email'],
            name=user_data['name'],
            role=user_data['role'],
            business_name=user_data.get('business_name'),
            business_email=user_data.get('business_email'),
            industry=user_data.get('industry'),
            team_size=user_data.get('team_size'),
            is_active=bool(user_data['is_active']),
            email_verified=bool(user_data['email_verified']),
            created_at=datetime.fromisoformat(user_data['created_at']),
            onboarding_completed=bool(user_data['onboarding_completed']),
            onboarding_step=user_data['onboarding_step'],
            metadata=metadata
        )
    
    def get_user_by_id(self, user_id: int) -> Optional[UserProfile]:
        """Get user profile by ID"""
        try:
            user_data = db_optimizer.execute_query(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            )
            
            if not user_data:
                return None
            
            return self._format_user_profile(user_data[0])
            
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        try:
            result = db_optimizer.execute_query(
                "UPDATE user_sessions SET is_valid = 0 WHERE expires_at < datetime('now')",
                fetch=False
            )
            return result
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
            return 0

# Global user auth manager instance
user_auth_manager = UserAuthManager()

# Export the authentication system
__all__ = ['UserAuthManager', 'user_auth_manager', 'UserProfile']
