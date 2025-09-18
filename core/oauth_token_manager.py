"""
OAuth Token Security and Refresh Management
Secure token storage, encryption, and automatic refresh with failure handling
"""

import os
import json
import logging
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import requests
from core.database_optimization import db_optimizer

# Gracefully handle missing cryptography
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    print("cryptography not available for token encryption")

logger = logging.getLogger(__name__)

class OAuthTokenManager:
    """Secure OAuth token management with encryption and refresh logic"""
    
    def __init__(self, db_optimizer):
        self.db_optimizer = db_optimizer
        if CRYPTOGRAPHY_AVAILABLE:
            self.encryption_key = self._get_or_create_encryption_key()
            self.cipher_suite = Fernet(self.encryption_key)
        else:
            self.encryption_key = None
            self.cipher_suite = None
        self._initialize_token_tables()
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for token storage"""
        try:
            # Try to get existing key from environment or database
            key_str = os.getenv('OAUTH_ENCRYPTION_KEY')
            if key_str:
                return key_str.encode()
            
            # Generate new key based on secret key
            secret_key = os.getenv('SECRET_KEY', 'default-secret-key')
            password = secret_key.encode()
            salt = b'fikiri_oauth_salt_2024'  # Fixed salt for consistency
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            return key
            
        except Exception as e:
            logger.error(f"Failed to get encryption key: {e}")
            # Fallback to a default key (not recommended for production)
            return Fernet.generate_key()
    
    def _initialize_token_tables(self):
        """Initialize OAuth token storage tables"""
        try:
            # OAuth tokens table with encryption
            self.db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS oauth_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    service TEXT NOT NULL,  -- 'gmail', 'outlook', etc.
                    access_token_encrypted TEXT NOT NULL,
                    refresh_token_encrypted TEXT,
                    token_type TEXT DEFAULT 'Bearer',
                    expires_at TIMESTAMP,
                    scope TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_refresh_at TIMESTAMP,
                    refresh_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    UNIQUE(user_id, service)
                )
            """, fetch=False)
            
            # OAuth refresh failures table
            self.db_optimizer.execute_query("""
                CREATE TABLE IF NOT EXISTS oauth_refresh_failures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    service TEXT NOT NULL,
                    failure_type TEXT NOT NULL,  -- 'refresh_failed', 'token_expired', 'revoked'
                    error_message TEXT,
                    http_status INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """, fetch=False)
            
            # Create indexes
            indexes = [
                ("idx_oauth_tokens_user_service", "oauth_tokens", ["user_id", "service"]),
                ("idx_oauth_tokens_expires_at", "oauth_tokens", ["expires_at"]),
                ("idx_oauth_tokens_is_active", "oauth_tokens", ["is_active"]),
                ("idx_oauth_refresh_failures_user", "oauth_refresh_failures", ["user_id"]),
                ("idx_oauth_refresh_failures_created_at", "oauth_refresh_failures", ["created_at"])
            ]
            
            for index_name, table, columns in indexes:
                try:
                    self.db_optimizer.execute_query(
                        f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({', '.join(columns)})",
                        fetch=False
                    )
                except Exception as e:
                    logger.warning(f"Failed to create index {index_name}: {e}")
            
            logger.info("OAuth token tables initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize OAuth token tables: {e}")
            raise
    
    def encrypt_token(self, token: str) -> str:
        """Encrypt token for secure storage"""
        if not CRYPTOGRAPHY_AVAILABLE or not self.cipher_suite:
            # Fallback to base64 encoding without encryption
            return base64.urlsafe_b64encode(token.encode()).decode()
        
        try:
            encrypted_bytes = self.cipher_suite.encrypt(token.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt token: {e}")
            raise
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt token from storage"""
        if not CRYPTOGRAPHY_AVAILABLE or not self.cipher_suite:
            # Fallback to base64 decoding without decryption
            return base64.urlsafe_b64decode(encrypted_token.encode()).decode()
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode())
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt token: {e}")
            raise
    
    def store_tokens(self, user_id: int, service: str, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store encrypted OAuth tokens"""
        try:
            # Encrypt tokens
            access_token_encrypted = self.encrypt_token(token_data['access_token'])
            refresh_token_encrypted = None
            if token_data.get('refresh_token'):
                refresh_token_encrypted = self.encrypt_token(token_data['refresh_token'])
            
            # Calculate expiry
            expires_at = None
            if token_data.get('expires_in'):
                expires_at = datetime.now() + timedelta(seconds=token_data['expires_in'])
            
            # Store in database
            self.db_optimizer.execute_query(
                """
                INSERT OR REPLACE INTO oauth_tokens 
                (user_id, service, access_token_encrypted, refresh_token_encrypted, 
                 token_type, expires_at, scope, updated_at, last_refresh_at, refresh_count, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, TRUE)
                """,
                (user_id, service, access_token_encrypted, refresh_token_encrypted,
                 token_data.get('token_type', 'Bearer'), expires_at, token_data.get('scope')),
                fetch=False
            )
            
            logger.info(f"Stored encrypted tokens for user {user_id}, service {service}")
            return {
                'success': True,
                'message': 'Tokens stored securely'
            }
            
        except Exception as e:
            logger.error(f"Failed to store tokens: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'TOKEN_STORE_FAILED'
            }
    
    def get_tokens(self, user_id: int, service: str) -> Dict[str, Any]:
        """Get decrypted OAuth tokens"""
        try:
            result = self.db_optimizer.execute_query(
                """
                SELECT access_token_encrypted, refresh_token_encrypted, token_type, 
                       expires_at, scope, is_active, last_refresh_at, refresh_count
                FROM oauth_tokens 
                WHERE user_id = ? AND service = ? AND is_active = TRUE
                """,
                (user_id, service)
            )
            
            if not result:
                return {
                    'success': False,
                    'error': 'No active tokens found',
                    'error_code': 'NO_TOKENS_FOUND'
                }
            
            row = result[0]
            
            # Decrypt tokens
            access_token = self.decrypt_token(row[0])
            refresh_token = self.decrypt_token(row[1]) if row[1] else None
            
            return {
                'success': True,
                'data': {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': row[2],
                    'expires_at': row[3],
                    'scope': row[4],
                    'is_active': bool(row[5]),
                    'last_refresh_at': row[6],
                    'refresh_count': row[7]
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get tokens: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'TOKEN_RETRIEVE_FAILED'
            }
    
    def refresh_token(self, user_id: int, service: str) -> Dict[str, Any]:
        """Refresh OAuth token with exponential backoff and failure handling"""
        try:
            # Get current tokens
            token_result = self.get_tokens(user_id, service)
            if not token_result['success']:
                return token_result
            
            tokens = token_result['data']
            refresh_token = tokens.get('refresh_token')
            
            if not refresh_token:
                return {
                    'success': False,
                    'error': 'No refresh token available',
                    'error_code': 'NO_REFRESH_TOKEN'
                }
            
            # Check if we should attempt refresh (rate limiting)
            if not self._should_attempt_refresh(user_id, service):
                return {
                    'success': False,
                    'error': 'Refresh rate limited due to recent failures',
                    'error_code': 'REFRESH_RATE_LIMITED'
                }
            
            # Attempt refresh based on service
            if service == 'gmail':
                return self._refresh_gmail_token(user_id, refresh_token)
            elif service == 'outlook':
                return self._refresh_outlook_token(user_id, refresh_token)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported service: {service}',
                    'error_code': 'UNSUPPORTED_SERVICE'
                }
                
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            self._log_refresh_failure(user_id, service, 'refresh_failed', str(e))
            return {
                'success': False,
                'error': str(e),
                'error_code': 'REFRESH_FAILED'
            }
    
    def _refresh_gmail_token(self, user_id: int, refresh_token: str) -> Dict[str, Any]:
        """Refresh Gmail OAuth token"""
        try:
            client_id = os.getenv('GMAIL_CLIENT_ID')
            client_secret = os.getenv('GMAIL_CLIENT_SECRET')
            
            if not client_id or not client_secret:
                raise Exception("Gmail OAuth credentials not configured")
            
            # Prepare refresh request
            refresh_data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            }
            
            # Make refresh request
            response = requests.post(
                'https://oauth2.googleapis.com/token',
                data=refresh_data,
                timeout=30
            )
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Store new tokens
                store_result = self.store_tokens(user_id, 'gmail', token_data)
                if store_result['success']:
                    # Update refresh count
                    self._update_refresh_count(user_id, 'gmail')
                    
                    logger.info(f"Successfully refreshed Gmail token for user {user_id}")
                    return {
                        'success': True,
                        'message': 'Token refreshed successfully',
                        'expires_in': token_data.get('expires_in')
                    }
                else:
                    raise Exception(f"Failed to store refreshed tokens: {store_result['error']}")
            else:
                error_msg = f"Gmail token refresh failed: {response.status_code} - {response.text}"
                self._log_refresh_failure(user_id, 'gmail', 'refresh_failed', error_msg, response.status_code)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Gmail token refresh failed: {e}")
            self._log_refresh_failure(user_id, 'gmail', 'refresh_failed', str(e))
            raise
    
    def _refresh_outlook_token(self, user_id: int, refresh_token: str) -> Dict[str, Any]:
        """Refresh Outlook OAuth token"""
        try:
            client_id = os.getenv('OUTLOOK_CLIENT_ID')
            client_secret = os.getenv('OUTLOOK_CLIENT_SECRET')
            
            if not client_id or not client_secret:
                raise Exception("Outlook OAuth credentials not configured")
            
            # Prepare refresh request
            refresh_data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token',
                'scope': 'https://graph.microsoft.com/Mail.ReadWrite'
            }
            
            # Make refresh request
            response = requests.post(
                'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                data=refresh_data,
                timeout=30
            )
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Store new tokens
                store_result = self.store_tokens(user_id, 'outlook', token_data)
                if store_result['success']:
                    # Update refresh count
                    self._update_refresh_count(user_id, 'outlook')
                    
                    logger.info(f"Successfully refreshed Outlook token for user {user_id}")
                    return {
                        'success': True,
                        'message': 'Token refreshed successfully',
                        'expires_in': token_data.get('expires_in')
                    }
                else:
                    raise Exception(f"Failed to store refreshed tokens: {store_result['error']}")
            else:
                error_msg = f"Outlook token refresh failed: {response.status_code} - {response.text}"
                self._log_refresh_failure(user_id, 'outlook', 'refresh_failed', error_msg, response.status_code)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Outlook token refresh failed: {e}")
            self._log_refresh_failure(user_id, 'outlook', 'refresh_failed', str(e))
            raise
    
    def _should_attempt_refresh(self, user_id: int, service: str) -> bool:
        """Check if we should attempt token refresh (rate limiting)"""
        try:
            # Check recent failures
            recent_failures = self.db_optimizer.execute_query(
                """
                SELECT COUNT(*) FROM oauth_refresh_failures 
                WHERE user_id = ? AND service = ? 
                AND created_at > datetime('now', '-15 minutes')
                """,
                (user_id, service)
            )
            
            failure_count = recent_failures[0][0] if recent_failures else 0
            
            # Allow refresh if less than 3 failures in last 15 minutes
            return failure_count < 3
            
        except Exception as e:
            logger.error(f"Failed to check refresh rate limit: {e}")
            return True  # Allow refresh on error
    
    def _log_refresh_failure(self, user_id: int, service: str, failure_type: str, 
                           error_message: str, http_status: Optional[int] = None):
        """Log OAuth refresh failure"""
        try:
            self.db_optimizer.execute_query(
                """
                INSERT INTO oauth_refresh_failures 
                (user_id, service, failure_type, error_message, http_status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, service, failure_type, error_message, http_status),
                fetch=False
            )
            
            logger.warning(f"OAuth refresh failure logged for user {user_id}, service {service}: {error_message}")
            
        except Exception as e:
            logger.error(f"Failed to log refresh failure: {e}")
    
    def _update_refresh_count(self, user_id: int, service: str):
        """Update refresh count for token"""
        try:
            self.db_optimizer.execute_query(
                """
                UPDATE oauth_tokens 
                SET refresh_count = refresh_count + 1, 
                    last_refresh_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND service = ?
                """,
                (user_id, service),
                fetch=False
            )
        except Exception as e:
            logger.error(f"Failed to update refresh count: {e}")
    
    def revoke_tokens(self, user_id: int, service: str) -> Dict[str, Any]:
        """Revoke OAuth tokens"""
        try:
            # Get tokens for revocation
            token_result = self.get_tokens(user_id, service)
            if not token_result['success']:
                return token_result
            
            tokens = token_result['data']
            access_token = tokens['access_token']
            
            # Revoke token with service
            if service == 'gmail':
                revoke_url = f"https://oauth2.googleapis.com/revoke?token={access_token}"
            elif service == 'outlook':
                revoke_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/logout"
            else:
                return {
                    'success': False,
                    'error': f'Unsupported service: {service}',
                    'error_code': 'UNSUPPORTED_SERVICE'
                }
            
            # Make revocation request
            response = requests.post(revoke_url, timeout=30)
            
            # Mark tokens as inactive regardless of response
            self.db_optimizer.execute_query(
                "UPDATE oauth_tokens SET is_active = FALSE WHERE user_id = ? AND service = ?",
                (user_id, service),
                fetch=False
            )
            
            logger.info(f"Revoked tokens for user {user_id}, service {service}")
            return {
                'success': True,
                'message': 'Tokens revoked successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to revoke tokens: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'REVOKE_FAILED'
            }
    
    def get_token_status(self, user_id: int, service: str) -> Dict[str, Any]:
        """Get comprehensive token status"""
        try:
            token_result = self.get_tokens(user_id, service)
            if not token_result['success']:
                return token_result
            
            tokens = token_result['data']
            
            # Check if token is expired
            is_expired = False
            if tokens['expires_at']:
                expires_at = datetime.fromisoformat(tokens['expires_at'])
                is_expired = datetime.now() >= expires_at
            
            # Get recent failure count
            recent_failures = self.db_optimizer.execute_query(
                """
                SELECT COUNT(*) FROM oauth_refresh_failures 
                WHERE user_id = ? AND service = ? 
                AND created_at > datetime('now', '-1 hour')
                """,
                (user_id, service)
            )
            failure_count = recent_failures[0][0] if recent_failures else 0
            
            # Determine status
            if is_expired:
                status = 'expired'
            elif failure_count >= 3:
                status = 'failed'
            elif tokens['refresh_count'] > 10:
                status = 'stale'
            else:
                status = 'active'
            
            return {
                'success': True,
                'data': {
                    'status': status,
                    'is_expired': is_expired,
                    'expires_at': tokens['expires_at'],
                    'last_refresh_at': tokens['last_refresh_at'],
                    'refresh_count': tokens['refresh_count'],
                    'recent_failures': failure_count,
                    'scope': tokens['scope'],
                    'token_hash': self._hash_token(tokens['access_token'])  # For debugging
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get token status: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_code': 'STATUS_CHECK_FAILED'
            }
    
    def _hash_token(self, token: str) -> str:
        """Create hash of token for debugging (last 4 chars + hash)"""
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()[:8]
            last_4 = token[-4:] if len(token) > 4 else token
            return f"{last_4}...{token_hash}"
        except Exception:
            return "***"

# Initialize OAuth token manager
oauth_token_manager = OAuthTokenManager(db_optimizer)
