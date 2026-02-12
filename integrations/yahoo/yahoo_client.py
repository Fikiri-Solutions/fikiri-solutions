#!/usr/bin/env python3
"""
Yahoo Mail OAuth2 Client for Fikiri Solutions
Implements OAuth2 authentication for Yahoo Mail IMAP/SMTP access
Note: Requires approval from Yahoo - see docs/YAHOO_INTEGRATION.md
"""

import os
import json
import logging
import requests
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class YahooOAuth2Client:
    """Yahoo Mail OAuth2 client with IMAP/SMTP support"""
    
    def __init__(self):
        self.client_id = os.getenv("YAHOO_CLIENT_ID")
        self.client_secret = os.getenv("YAHOO_CLIENT_SECRET")
        self.redirect_uri = os.getenv("YAHOO_REDIRECT_URI", "http://localhost:5000/api/oauth/yahoo/callback")
        
        # Yahoo OAuth2 endpoints
        self.auth_url = "https://api.login.yahoo.com/oauth2/request_auth"
        self.token_url = "https://api.login.yahoo.com/oauth2/get_token"
        
        # Required scopes for IMAP/SMTP access (requires Yahoo approval)
        self.scopes = [
            "mail-r",  # Read mail via IMAP
            "mail-w",  # Write mail via SMTP
            "mail-d",  # Delete mail
        ]
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate Yahoo OAuth2 authorization URL"""
        if not self.client_id:
            raise ValueError("YAHOO_CLIENT_ID not configured")
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.scopes),
            'state': state or 'yahoo_auth'
        }
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{self.auth_url}?{query_string}"
    
    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        if not self.client_id or not self.client_secret:
            raise ValueError("Yahoo OAuth2 credentials not configured")
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        response = requests.post(self.token_url, data=data, auth=(self.client_id, self.client_secret))
        response.raise_for_status()
        
        token_data = response.json()
        return {
            'access_token': token_data.get('access_token'),
            'refresh_token': token_data.get('refresh_token'),
            'expires_in': token_data.get('expires_in', 3600),
            'token_type': token_data.get('token_type', 'Bearer'),
            'xoauth_yahoo_guid': token_data.get('xoauth_yahoo_guid')
        }
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        if not self.client_id or not self.client_secret:
            raise ValueError("Yahoo OAuth2 credentials not configured")
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        response = requests.post(self.token_url, data=data, auth=(self.client_id, self.client_secret))
        response.raise_for_status()
        
        token_data = response.json()
        return {
            'access_token': token_data.get('access_token'),
            'refresh_token': token_data.get('refresh_token', refresh_token),
            'expires_in': token_data.get('expires_in', 3600),
            'token_type': token_data.get('token_type', 'Bearer')
        }
    
    def get_imap_oauth_string(self, access_token: str, email: str) -> str:
        """Generate OAuth2 string for IMAP authentication"""
        return f"user={email}\x01auth=Bearer {access_token}\x01\x01"
    
    def get_smtp_oauth_string(self, access_token: str, email: str) -> str:
        """Generate OAuth2 string for SMTP authentication"""
        return f"user={email}\x01auth=Bearer {access_token}\x01\x01"

