#!/usr/bin/env python3
"""
Fikiri Solutions - Gmail Authentication Service
Handles Gmail API authentication and token management.
"""

import os
import pickle
import logging
from pathlib import Path
from typing import Optional, List
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

class GmailAuthenticator:
    """Gmail API authentication handler."""
    
    # Gmail API scopes
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.compose'
    ]
    
    def __init__(self, credentials_path: str, token_path: str):
        """
        Initialize Gmail authenticator.
        
        Args:
            credentials_path: Path to Google OAuth2 credentials JSON file
            token_path: Path to store/load authentication token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.logger = logging.getLogger(__name__)
    
    def authenticate(self) -> Optional[object]:
        """
        Authenticate with Gmail API.
        
        Returns:
            Gmail service object if successful, None otherwise
        """
        try:
            creds = self._load_or_create_credentials()
            if not creds:
                return None
            
            # Create Gmail service
            from googleapiclient.discovery import build
            service = build('gmail', 'v1', credentials=creds)
            
            self.logger.info("✅ Gmail authentication successful")
            return service
            
        except Exception as e:
            self.logger.error(f"❌ Gmail authentication failed: {e}")
            return None
    
    def _load_or_create_credentials(self) -> Optional[Credentials]:
        """Load existing credentials or create new ones."""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
                self.logger.info("📁 Loaded existing credentials")
            except Exception as e:
                self.logger.warning(f"⚠️ Could not load existing token: {e}")
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.logger.info("🔄 Refreshed expired credentials")
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not refresh credentials: {e}")
                    creds = None
            
            if not creds:
                creds = self._get_new_credentials()
                if not creds:
                    return None
            
            # Save credentials for next time
            try:
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
                self.logger.info("💾 Saved new credentials")
            except Exception as e:
                self.logger.warning(f"⚠️ Could not save credentials: {e}")
        
        return creds
    
    def _get_new_credentials(self) -> Optional[Credentials]:
        """Get new credentials through OAuth2 flow."""
        if not os.path.exists(self.credentials_path):
            self.logger.error(f"❌ Credentials file not found: {self.credentials_path}")
            self.logger.info("📝 Please download your OAuth2 credentials from Google Cloud Console")
            self.logger.info("🔗 Go to: https://console.cloud.google.com/apis/credentials")
            return None
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path, 
                self.SCOPES
            )
            creds = flow.run_local_server(port=0)
            self.logger.info("✅ New credentials obtained successfully")
            return creds
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get new credentials: {e}")
            return None
    
    def revoke_credentials(self) -> bool:
        """Revoke current credentials."""
        try:
            if os.path.exists(self.token_path):
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
                
                if creds and creds.valid:
                    creds.revoke(Request())
                
                os.remove(self.token_path)
                self.logger.info("🗑️ Credentials revoked and token removed")
                return True
        except Exception as e:
            self.logger.error(f"❌ Failed to revoke credentials: {e}")
        
        return False
    
    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        try:
            if os.path.exists(self.token_path):
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
                return creds and creds.valid
        except Exception:
            pass
        return False

def authenticate_gmail(credentials_path: str = "auth/credentials.json", 
                      token_path: str = "auth/token.pkl") -> Optional[object]:
    """
    Convenience function to authenticate with Gmail.
    
    Args:
        credentials_path: Path to credentials file
        token_path: Path to token file
        
    Returns:
        Gmail service object if successful, None otherwise
    """
    authenticator = GmailAuthenticator(credentials_path, token_path)
    return authenticator.authenticate()
