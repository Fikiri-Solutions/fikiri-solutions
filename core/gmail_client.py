#!/usr/bin/env python3
"""
Gmail Client with Automatic Token Refresh
Production-grade Gmail API client with automatic token handling
Based on proven patterns from real-world applications
"""

import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Try to import Google API libraries
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    logger.warning("⚠️ Google API libraries not available")

# Try to import cryptography for token encryption
try:
    from cryptography.fernet import Fernet
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

class GmailClient:
    """Production Gmail client with automatic token refresh"""
    
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        
        # Initialize encryption if available
        fernet_key = os.getenv("FERNET_KEY")
        if CRYPTOGRAPHY_AVAILABLE and fernet_key:
            self.fernet = Fernet(fernet_key.encode())
            self.encryption_enabled = True
        else:
            self.fernet = None
            self.encryption_enabled = False
            logger.warning("⚠️ Token encryption disabled")
    
    def _dec(s: str, fernet: Optional[Fernet], enabled: bool) -> str:
        """Decrypt token from storage"""
        if enabled and fernet:
            return fernet.decrypt(s.encode()).decode()
        else:
            # Fallback to base64 decoding for development
            import base64
            return base64.b64decode(s.encode()).decode()
    
    def _enc(self, s: str) -> str:
        """Encrypt token for storage"""
        if self.encryption_enabled and self.fernet:
            return self.fernet.encrypt(s.encode()).decode()
        else:
            # Fallback to base64 encoding for development
            import base64
            return base64.b64encode(s.encode()).decode()
    
    def _get_gmail_tokens(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve Gmail tokens from database"""
        try:
            from core.database_optimization import db_optimizer
            
            result = db_optimizer.execute_query("""
                SELECT access_token_enc, refresh_token_enc, expiry_timestamp, scopes_json
                FROM gmail_tokens 
                WHERE user_id = ? AND is_active = TRUE
                ORDER BY updated_at DESC
                LIMIT 1
            """, (user_id,))
            
            if not result:
                return None
                
            row = result[0]
            return {
                'access_token': self._dec(row['access_token_enc'], self.fernet, self.encryption_enabled),
                'refresh_token': self._dec(row['refresh_token_enc'], self.fernet, self.encryption_enabled) if row['refresh_token_enc'] else None,
                'expiry': datetime.fromtimestamp(row['expiry_timestamp']) if row['expiry_timestamp'] else None,
                'scopes': json.loads(row['scopes_json']) if row['scopes_json'] else []
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get tokens for user {user_id}: {e}")
            return None
    
    def _save_gmail_tokens(self, user_id: int, access_token: str, refresh_token: Optional[str] = None, expiry: Optional[datetime] = None):
        """Save refreshed tokens to database"""
        try:
            from core.database_optimization import db_optimizer
            
            db_optimizer.execute_query("""
                UPDATE gmail_tokens 
                SET access_token_enc = ?, refresh_token_enc = ?, 
                    expiry_timestamp = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND is_active = TRUE
            """, (
                self._enc(access_token),
                self._enc(refresh_token) if refresh_token else None,
                int(expiry.timestamp()) if expiry else None,
                user_id
            ), fetch=False)
            
            logger.info(f"✅ Tokens saved for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save tokens for user {user_id}: {e}")
            raise
    
    def get_credentials_for_user(self, user_id: int) -> Optional[Credentials]:
        """Get valid Gmail credentials for user with auto-refresh"""
        try:
            token_data = self._get_gmail_tokens(user_id)
            if not token_data:
                logger.error(f"❌ No Gmail tokens found for user {user_id}")
                return None
            
            if not GOOGLE_API_AVAILABLE:
                logger.error("❌ Google API libraries not available")
                return None
            
            # Create credentials object
            creds = Credentials(
                token=token_data['access_token'],
                refresh_token=token_data['refresh_token'],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=token_data['scopes'],
            )
            
            # Check if token needs refresh
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    logger.info(f"🔄 Refreshing token for user {user_id}")
                    try:
                        creds.refresh(Request())
                        
                        # Save refreshed tokens
                        self._save_gmail_tokens(
                            user_id,
                            creds.token,
                            creds.refresh_token,
                            creds.expiry
                        )
                        
                        logger.info(f"✅ Token refreshed successfully for user {user_id}")
                        
                    except Exception as e:
                        logger.error(f"❌ Token refresh failed for user {user_id}: {e}")
                        return None
                else:
                    logger.error(f"❌ Gmail credentials not refreshable for user {user_id}")
                    return None
            
            return creds
            
        except Exception as e:
            logger.error(f"❌ Failed to get credentials for user {user_id}: {e}")
            return None
    
    def get_gmail_service_for_user(self, user_id: int):
        """Get Gmail service for user with automatic token refresh"""
        try:
            creds = self.get_credentials_for_user(user_id)
            if not creds:
                raise RuntimeError(f"No valid Gmail credentials for user {user_id}")
            
            # Build service with credentials
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            
            logger.info(f"✅ Gmail service created for user {user_id}")
            return service
            
        except Exception as e:
            logger.error(f"❌ Failed to create Gmail service for user {user_id}: {e}")
            raise RuntimeError(f"Gmail service creation failed: {str(e)}")

# Global client instance
gmail_client = GmailClient()
