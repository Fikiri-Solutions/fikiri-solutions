#!/usr/bin/env python3
"""
Google OAuth Integration with Offline Access
Enhanced OAuth flow with refresh tokens, state management, and secure token storage
"""

import os
import json
import time
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode, parse_qs
import requests

from core.database_optimization import db_optimizer
from core.oauth_token_manager import oauth_token_manager

logger = logging.getLogger(__name__)

class GoogleOAuthManager:
    """Enhanced Google OAuth integration with offline access and refresh tokens"""
    
    def __init__(self):
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'https://fikirisolutions.com/auth/google/callback')
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]
        self.token_url = 'https://oauth2.googleapis.com/token'
        self.auth_url = 'https://accounts.google.com/o/oauth2/v2/auth'
        self.userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        self._initialize_tables()
    
    def _initialize_tables(self):
        """Initialize database tables for OAuth management"""
        try:
            # Create OAuth states table for CSRF protection
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS oauth_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    state TEXT NOT NULL UNIQUE,
                    user_id INTEGER,
                    provider TEXT NOT NULL,
                    redirect_url TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NOT NULL,
                    is_used BOOLEAN DEFAULT FALSE,
                    metadata TEXT DEFAULT '{}'
                )
            """, fetch=False)
            
            # Create index for faster lookups
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_oauth_states_state 
                ON oauth_states (state)
            """, fetch=False)
            
            # Create Google OAuth tokens table
            db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS google_oauth_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT,
                    token_type TEXT DEFAULT 'Bearer',
                    expires_at DATETIME,
                    scope TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """, fetch=False)
            
            # Create indexes
            db_optimizer.execute_query("""
                CREATE INDEX IF NOT EXISTS idx_google_tokens_user_id 
                ON google_oauth_tokens (user_id)
            """, fetch=False)
            
            logger.info("✅ Google OAuth tables initialized")
            
        except Exception as e:
            logger.error(f"❌ Google OAuth table initialization failed: {e}")
    
    def generate_auth_url(self, user_id: int, redirect_url: str = None, 
                         metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate Google OAuth authorization URL with state protection"""
        try:
            # Generate secure state parameter
            state = secrets.token_urlsafe(32)
            
            # Store state in database with expiration
            expires_at = datetime.utcnow() + timedelta(minutes=10)  # 10 minutes
            db_optimizer.execute_query("""
                INSERT INTO oauth_states 
                (state, user_id, provider, redirect_url, expires_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                state,
                user_id,
                'google',
                redirect_url,
                expires_at.isoformat(),
                json.dumps(metadata or {})
            ), fetch=False)
            
            # Build authorization URL
            params = {
                'client_id': self.client_id,
                'redirect_uri': self.redirect_uri,
                'scope': ' '.join(self.scopes),
                'response_type': 'code',
                'access_type': 'offline',  # Request refresh token
                'prompt': 'consent',  # Force consent screen to get refresh token
                'state': state,
                'include_granted_scopes': 'true'
            }
            
            auth_url = f"{self.auth_url}?{urlencode(params)}"
            
            logger.info(f"✅ Generated Google OAuth URL for user {user_id}")
            
            return {
                'success': True,
                'auth_url': auth_url,
                'state': state,
                'expires_at': expires_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ OAuth URL generation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'OAUTH_URL_GENERATION_FAILED'
            }
    
    def handle_oauth_callback(self, code: str, state: str) -> Dict[str, Any]:
        """Handle OAuth callback and exchange code for tokens"""
        try:
            # Verify state
            state_data = db_optimizer.execute_query("""
                SELECT * FROM oauth_states 
                WHERE state = ? AND is_used = FALSE AND expires_at > datetime('now')
            """, (state,))
            
            if not state_data:
                return {
                    'success': False,
                    'error': 'Invalid or expired state',
                    'error_code': 'INVALID_STATE'
                }
            
            state_record = state_data[0]
            user_id = state_record['user_id']
            
            # Mark state as used
            db_optimizer.execute_query("""
                UPDATE oauth_states SET is_used = TRUE WHERE state = ?
            """, (state,), fetch=False)
            
            # Exchange code for tokens
            token_data = self._exchange_code_for_tokens(code)
            
            if not token_data['success']:
                return token_data
            
            # Get user info from Google
            user_info = self._get_user_info(token_data['access_token'])
            
            if not user_info['success']:
                return user_info
            
            # Store tokens in database
            token_result = self._store_tokens(user_id, token_data['tokens'], user_info['user_info'])
            
            if not token_result['success']:
                return token_result
            
            # Update user onboarding status
            try:
                from core.user_auth import user_auth_manager
                user_auth_manager.update_user_profile(
                    user_id=user_id,
                    onboarding_step=2  # Gmail connected step
                )
            except Exception as e:
                logger.warning(f"Failed to update onboarding status: {e}")
                # Don't fail the OAuth callback for onboarding issues
            
            logger.info(f"✅ Google OAuth completed for user {user_id}")
            
            return {
                'success': True,
                'user_id': user_id,
                'tokens': token_data['tokens'],
                'user_info': user_info['user_info'],
                'redirect_url': state_record['redirect_url']
            }
            
        except Exception as e:
            logger.error(f"❌ OAuth callback handling failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'OAUTH_CALLBACK_FAILED'
            }
    
    def _exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens"""
        try:
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': self.redirect_uri
            }
            
            response = requests.post(self.token_url, data=data, timeout=30)
            response.raise_for_status()
            
            token_response = response.json()
            
            # Calculate expiration time
            expires_at = None
            if 'expires_in' in token_response:
                expires_at = datetime.utcnow() + timedelta(seconds=token_response['expires_in'])
            
            tokens = {
                'access_token': token_response['access_token'],
                'refresh_token': token_response.get('refresh_token'),
                'token_type': token_response.get('token_type', 'Bearer'),
                'expires_at': expires_at.isoformat() if expires_at else None,
                'scope': token_response.get('scope', '')
            }
            
            return {
                'success': True,
                'tokens': tokens
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Token exchange failed: {e}")
            return {
                'success': False,
                'error': f'Token exchange failed: {str(e)}',
                'error_code': 'TOKEN_EXCHANGE_FAILED'
            }
        except Exception as e:
            logger.error(f"❌ Token exchange error: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'TOKEN_EXCHANGE_ERROR'
            }
    
    def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Google"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}'
            }
            
            response = requests.get(self.userinfo_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            user_info = response.json()
            
            return {
                'success': True,
                'user_info': {
                    'google_id': user_info.get('id'),
                    'email': user_info.get('email'),
                    'name': user_info.get('name'),
                    'given_name': user_info.get('given_name'),
                    'family_name': user_info.get('family_name'),
                    'picture': user_info.get('picture'),
                    'verified_email': user_info.get('verified_email', False)
                }
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ User info retrieval failed: {e}")
            return {
                'success': False,
                'error': f'User info retrieval failed: {str(e)}',
                'error_code': 'USER_INFO_FAILED'
            }
        except Exception as e:
            logger.error(f"❌ User info error: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'USER_INFO_ERROR'
            }
    
    def _store_tokens(self, user_id: int, tokens: Dict[str, Any], 
                     user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Store OAuth tokens securely in database"""
        try:
            # Deactivate existing tokens for this user
            db_optimizer.execute_query("""
                UPDATE google_oauth_tokens SET is_active = FALSE WHERE user_id = ?
            """, (user_id,), fetch=False)
            
            # Store new tokens
            token_id = db_optimizer.execute_query("""
                INSERT INTO google_oauth_tokens 
                (user_id, access_token, refresh_token, token_type, expires_at, scope, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                tokens['access_token'],
                tokens['refresh_token'],
                tokens['token_type'],
                tokens['expires_at'],
                tokens['scope'],
                json.dumps({
                    'user_info': user_info,
                    'created_via': 'oauth_callback'
                })
            ), fetch=False)
            
            # Update user profile with Google info if needed
            if user_info.get('email'):
                db_optimizer.execute_query("""
                    UPDATE users SET 
                        metadata = json_set(metadata, '$.google_connected', TRUE),
                        metadata = json_set(metadata, '$.google_email', ?),
                        metadata = json_set(metadata, '$.google_name', ?)
                    WHERE id = ?
                """, (
                    user_info['email'],
                    user_info['name'],
                    user_id
                ), fetch=False)
            
            logger.info(f"✅ Stored Google OAuth tokens for user {user_id}")
            
            return {
                'success': True,
                'token_id': token_id
            }
            
        except Exception as e:
            logger.error(f"❌ Token storage failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'TOKEN_STORAGE_FAILED'
            }
    
    def refresh_access_token(self, user_id: int) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        try:
            # Get current tokens
            token_data = db_optimizer.execute_query("""
                SELECT * FROM google_oauth_tokens 
                WHERE user_id = ? AND is_active = TRUE AND refresh_token IS NOT NULL
            """, (user_id,))
            
            if not token_data:
                return {
                    'success': False,
                    'error': 'No active refresh token found',
                    'error_code': 'NO_REFRESH_TOKEN'
                }
            
            token_record = token_data[0]
            refresh_token = token_record['refresh_token']
            
            # Request new access token
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(self.token_url, data=data, timeout=30)
            response.raise_for_status()
            
            token_response = response.json()
            
            # Calculate new expiration time
            expires_at = None
            if 'expires_in' in token_response:
                expires_at = datetime.utcnow() + timedelta(seconds=token_response['expires_in'])
            
            # Update tokens in database
            db_optimizer.execute_query("""
                UPDATE google_oauth_tokens 
                SET access_token = ?, expires_at = ?, metadata = json_set(metadata, '$.last_refresh', ?)
                WHERE id = ?
            """, (
                token_response['access_token'],
                expires_at.isoformat() if expires_at else None,
                datetime.utcnow().isoformat(),
                token_record['id']
            ), fetch=False)
            
            logger.info(f"✅ Refreshed Google OAuth token for user {user_id}")
            
            return {
                'success': True,
                'access_token': token_response['access_token'],
                'expires_at': expires_at.isoformat() if expires_at else None
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Token refresh failed: {e}")
            return {
                'success': False,
                'error': f'Token refresh failed: {str(e)}',
                'error_code': 'TOKEN_REFRESH_FAILED'
            }
        except Exception as e:
            logger.error(f"❌ Token refresh error: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'TOKEN_REFRESH_ERROR'
            }
    
    def get_valid_access_token(self, user_id: int) -> Optional[str]:
        """Get a valid access token, refreshing if necessary"""
        try:
            # Get current tokens
            token_data = db_optimizer.execute_query("""
                SELECT * FROM google_oauth_tokens 
                WHERE user_id = ? AND is_active = TRUE
            """, (user_id,))
            
            if not token_data:
                return None
            
            token_record = token_data[0]
            access_token = token_record['access_token']
            expires_at = token_record['expires_at']
            
            # Check if token is expired
            if expires_at:
                expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if datetime.utcnow() >= expires_datetime:
                    # Token expired, try to refresh
                    refresh_result = self.refresh_access_token(user_id)
                    if refresh_result['success']:
                        return refresh_result['access_token']
                    else:
                        return None
            
            return access_token
            
        except Exception as e:
            logger.error(f"❌ Access token retrieval failed: {e}")
            return None
    
    def revoke_tokens(self, user_id: int) -> bool:
        """Revoke OAuth tokens for a user"""
        try:
            # Get tokens to revoke
            token_data = db_optimizer.execute_query("""
                SELECT access_token, refresh_token FROM google_oauth_tokens 
                WHERE user_id = ? AND is_active = TRUE
            """, (user_id,))
            
            # Revoke tokens with Google
            for token_record in token_data:
                if token_record['access_token']:
                    try:
                        requests.post(
                            'https://oauth2.googleapis.com/revoke',
                            data={'token': token_record['access_token']},
                            timeout=10
                        )
                    except:
                        pass  # Continue even if revocation fails
            
            # Mark tokens as inactive in database
            db_optimizer.execute_query("""
                UPDATE google_oauth_tokens SET is_active = FALSE WHERE user_id = ?
            """, (user_id,), fetch=False)
            
            # Update user metadata
            db_optimizer.execute_query("""
                UPDATE users SET 
                    metadata = json_set(metadata, '$.google_connected', FALSE)
                WHERE id = ?
            """, (user_id,), fetch=False)
            
            logger.info(f"✅ Revoked Google OAuth tokens for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Token revocation failed: {e}")
            return False
    
    def cleanup_expired_states(self):
        """Clean up expired OAuth states"""
        try:
            db_optimizer.execute_query("""
                DELETE FROM oauth_states 
                WHERE expires_at < datetime('now') OR is_used = TRUE
            """, fetch=False)
            
            logger.info("✅ Expired OAuth states cleaned up")
            
        except Exception as e:
            logger.error(f"❌ OAuth state cleanup failed: {e}")

# Global Google OAuth manager
google_oauth_manager = GoogleOAuthManager()
