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
        """Verify password safely, handling serialization edge cases."""
        try:
            if not salt:
                logger.warning("No salt found; regenerating PBKDF2 with blank salt.")
                salt = ''
            
            # Handle JSON-encoded or array-wrapped salts
            if isinstance(salt, (list, dict)):
                salt = next(iter(salt.values() if isinstance(salt, dict) else salt), '')
            
            if isinstance(salt, str):
                salt = salt.strip()
                # Handle strings like '["abc"]' or '[abc]'
                if salt.startswith('[') and salt.endswith(']'):
                    salt = salt.strip('[]').replace('"', '').replace("'", "")
            
            # Only allow hex or ASCII salts
            try:
                bytes.fromhex(salt)
            except ValueError:
                salt = salt.encode('utf-8').hex()
            
            candidate_hash, _ = self._hash_password(password, salt)
            return secrets.compare_digest(candidate_hash, stored_hash)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def _verify_legacy_password(self, password: str, stored_hash: str) -> bool:
        """Support legacy plaintext or simple SHA-256 hashes for migrated users."""
        try:
            import hashlib
            # In case early dev builds stored plain or SHA256 only
            simple_hash = hashlib.sha256(password.encode()).hexdigest()
            return secrets.compare_digest(simple_hash, stored_hash)
        except Exception as e:
            logger.error(f"Legacy password verification error: {e}")
            return False
    
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
            
            # Ensure salt always exists
            if not salt:
                salt = secrets.token_hex(self.salt_length)
                logger.warning(f"Generated new salt for user {email}")
            
            # Create user record - we need to get the lastrowid, so let's do this manually
            try:
                with db_optimizer.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """INSERT INTO users 
                           (email, name, password_hash, business_name, business_email, 
                            industry, team_size, metadata, role, is_active, email_verified, 
                            onboarding_completed, onboarding_step) 
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (email, name, password_hash, business_name, business_email,
                         industry, team_size, json.dumps({'salt': str(salt)}), 'user', True, False, False, 1)
                    )
                    user_id = cursor.lastrowid
                    conn.commit()
            except Exception as e:
                logger.error(f"Error inserting user: {e}")
                raise
            
            # Get the created user (rulepack compliance: specific columns, not SELECT *)
            user_data = db_optimizer.execute_query(
                "SELECT id, email, name, role, business_name, business_email, industry, team_size, is_active, email_verified, created_at, updated_at, last_login, onboarding_completed, onboarding_step, metadata FROM users WHERE id = ?",
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
            # Get user data (rulepack compliance: specific columns, including password_hash for auth)
            user_data = db_optimizer.execute_query(
                "SELECT id, email, name, password_hash, role, business_name, business_email, industry, team_size, is_active, email_verified, created_at, updated_at, last_login, onboarding_completed, onboarding_step, metadata FROM users WHERE email = ? AND is_active = 1",
                (email,)
            )
            
            if not user_data:
                logger.warning(f"No user found for email: {email}")
                return {
                    'success': False,
                    'error': 'Invalid email or password',
                    'error_code': 'INVALID_CREDENTIALS'
                }
            
            user = user_data[0]
            # Handle SQLite Row objects by converting to dict
            if hasattr(user, 'keys'):
                user_dict = dict(user)
            else:
                user_dict = user
                
            metadata = json.loads(user_dict.get('metadata', '{}'))
            salt = metadata.get('salt', '')
            
            # Debug logging
            logger.info(f"Authentication attempt for {email}")
            logger.info(f"User ID: {user_dict.get('id')}")
            logger.info(f"Password hash length: {len(user_dict.get('password_hash', ''))}")
            logger.info(f"Salt length: {len(salt)}")
            logger.info(f"Metadata: {metadata}")
            
            # Verify password
            password_hash = user_dict.get('password_hash', '')
            if not password_hash:
                logger.warning(f"No password hash found for user {email}")
                return {
                    'success': False,
                    'error': 'Invalid email or password',
                    'error_code': 'INVALID_CREDENTIALS'
                }
            
            if not self._verify_password(password, password_hash, salt):
                # Try legacy password verification as fallback
                if not self._verify_legacy_password(password, password_hash):
                    logger.warning(f"Password verification failed for user {email}")
                    return {
                        'success': False,
                        'error': 'Invalid email or password',
                        'error_code': 'INVALID_CREDENTIALS'
                    }
                else:
                    logger.info(f"Legacy password verification succeeded for user {email}")
            
            # Create session
            session_result = self._create_session(
                user_dict['id'], ip_address, user_agent
            )
            
            # Update last login
            db_optimizer.execute_query(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (user_dict['id'],),
                fetch=False
            )
            
            logger.info(f"User authenticated successfully: {email}")
            
            # Generate JWT tokens
            try:
                from core.jwt_auth import get_jwt_manager
                jwt_tokens = get_jwt_manager().generate_tokens(
                    user_dict['id'],
                    user_dict,
                    device_info=user_agent,
                    ip_address=ip_address
                )
            except Exception as e:
                logger.error(f"JWT token generation failed: {e}")
                jwt_tokens = None
            
            return {
                'success': True,
                'user': self._format_user_profile(user),
                'tokens': jwt_tokens,
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
        """Update user profile information. updates may include metadata_updates dict for phone/sms_consent."""
        try:
            metadata_updates = updates.pop('metadata_updates', None)
            if metadata_updates is not None:
                row = db_optimizer.execute_query(
                    "SELECT metadata FROM users WHERE id = ? AND is_active = 1",
                    (user_id,)
                )
                meta = json.loads((row[0].get('metadata') or '{}') if row else '{}')
                meta.update(metadata_updates)
                db_optimizer.execute_query(
                    "UPDATE users SET metadata = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (json.dumps(meta), user_id),
                    fetch=False
                )

            # Build update query dynamically for column fields
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
            
            if update_fields:
                update_values.append(user_id)
                query = f"UPDATE users SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
                db_optimizer.execute_query(query, tuple(update_values), fetch=False)
            
            # Get updated user data (rulepack compliance: specific columns, not SELECT *)
            user_data = db_optimizer.execute_query(
                "SELECT id, email, name, role, business_name, business_email, industry, team_size, is_active, email_verified, created_at, updated_at, last_login, onboarding_completed, onboarding_step, metadata FROM users WHERE id = ?",
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
    
    def request_password_reset(self, email: str) -> Dict[str, Any]:
        """Request password reset for user"""
        try:
            # Check if user exists
            user_data = db_optimizer.execute_query(
                "SELECT id, email, name FROM users WHERE email = ? AND is_active = 1",
                (email,)
            )
            
            if not user_data:
                # Always return success to prevent email enumeration
                return {
                    'success': True,
                    'message': 'If an account exists, a reset link has been sent'
                }
            
            user = user_data[0]
            
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            
            # Store reset token in user metadata
            metadata = json.loads(user.get('metadata', '{}'))
            metadata['reset_token'] = reset_token
            metadata['reset_token_expires'] = int(time.time()) + 3600  # 1 hour
            
            db_optimizer.execute_query(
                "UPDATE users SET metadata = ? WHERE id = ?",
                (json.dumps(metadata), user['id']),
                fetch=False
            )
            
            # Queue password reset email
            from email_automation.jobs import email_job_manager
            email_job_manager.queue_password_reset_email(
                email=email,
                reset_token=reset_token,
                name=user.get('name', 'User')
            )
            
            logger.info(f"Password reset requested for {email}")
            
            return {
                'success': True,
                'message': 'If an account exists, a reset link has been sent'
            }
            
        except Exception as e:
            logger.error(f"Error requesting password reset: {e}")
            return {
                'success': False,
                'error': 'Failed to process password reset request',
                'error_code': 'PASSWORD_RESET_ERROR'
            }
    
    def reset_user_password(self, user_id: int, new_password: str) -> Dict[str, Any]:
        """Reset user password with new password"""
        try:
            # Hash new password
            new_password_hash, new_salt = self._hash_password(new_password)
            
            # Update password and salt in metadata
            user_data = db_optimizer.execute_query(
                "SELECT metadata FROM users WHERE id = ?",
                (user_id,)
            )[0]
            
            metadata = json.loads(user_data['metadata'] or '{}')
            metadata['salt'] = str(new_salt)
            # Remove reset token
            metadata.pop('reset_token', None)
            metadata.pop('reset_token_expires', None)
            
            db_optimizer.execute_query(
                "UPDATE users SET password_hash = ?, metadata = ? WHERE id = ?",
                (new_password_hash, json.dumps(metadata), user_id),
                fetch=False
            )
            
            # Revoke all existing sessions
            self.revoke_all_user_sessions(user_id)
            try:
                from core.jwt_auth import get_jwt_manager
                get_jwt_manager().revoke_all_refresh_tokens(user_id)
            except Exception as revoke_error:
                logger.warning("Failed to revoke refresh tokens on password reset: %s", revoke_error)
            
            logger.info(f"Password reset completed for user {user_id}")
            
            return {
                'success': True,
                'message': 'Password reset successfully'
            }
            
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return {
                'success': False,
                'error': 'Failed to reset password',
                'error_code': 'PASSWORD_RESET_ERROR'
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
            metadata['salt'] = str(new_salt)
            db_optimizer.execute_query(
                "UPDATE users SET password_hash = ?, metadata = ? WHERE id = ?",
                (new_password_hash, json.dumps(metadata), user_id),
                fetch=False
            )
            
            # Revoke all existing sessions
            self.revoke_all_user_sessions(user_id)
            try:
                from core.jwt_auth import get_jwt_manager
                get_jwt_manager().revoke_all_refresh_tokens(user_id)
            except Exception as revoke_error:
                logger.warning("Failed to revoke refresh tokens on password change: %s", revoke_error)
            
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
        # Handle SQLite Row objects by converting to dict
        if hasattr(user_data, 'keys'):
            user_dict = dict(user_data)
        else:
            user_dict = user_data
            
        metadata = json.loads(user_dict.get('metadata', '{}'))
        
        return UserProfile(
            id=user_dict['id'],
            email=user_dict['email'],
            name=user_dict['name'],
            role=user_dict.get('role', 'user'),
            business_name=user_dict.get('business_name'),
            business_email=user_dict.get('business_email'),
            industry=user_dict.get('industry'),
            team_size=user_dict.get('team_size'),
            is_active=bool(user_dict.get('is_active', True)),
            email_verified=bool(user_dict.get('email_verified', False)),
            created_at=datetime.fromisoformat(user_dict['created_at']),
            onboarding_completed=bool(user_dict.get('onboarding_completed', False)),
            onboarding_step=user_dict.get('onboarding_step', 1),
            metadata=metadata
        )
    
    def get_user_by_id(self, user_id: int) -> Optional[UserProfile]:
        """Get user profile by ID"""
        try:
            # Rulepack compliance: specific columns, not SELECT *
            user_data = db_optimizer.execute_query(
                "SELECT id, email, name, role, business_name, business_email, industry, team_size, is_active, email_verified, created_at, updated_at, last_login, onboarding_completed, onboarding_step, metadata FROM users WHERE id = ?",
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
