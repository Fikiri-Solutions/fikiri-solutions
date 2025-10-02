"""
Gmail OAuth Integration System
Handles Gmail OAuth flow, token management, and email synchronization
"""

import json
import time
import logging
import secrets
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs
import requests
from core.database_optimization import db_optimizer
from core.user_auth import user_auth_manager

logger = logging.getLogger(__name__)

@dataclass
class GmailToken:
    """Gmail OAuth token data structure"""
    id: int
    user_id: int
    access_token: str
    refresh_token: Optional[str]
    token_type: str
    expires_at: Optional[datetime]
    scope: str
    created_at: datetime
    is_active: bool

@dataclass
class EmailSyncStatus:
    """Email sync status data structure"""
    id: int
    user_id: int
    sync_type: str
    status: str
    emails_processed: int
    emails_total: int
    started_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    metadata: Dict[str, Any]

class GmailOAuthManager:
    """Gmail OAuth integration and token management"""
    
    def __init__(self):
        self.client_id = None
        self.client_secret = None
        self.redirect_uri = None
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.modify'
        ]
        self.token_url = 'https://oauth2.googleapis.com/token'
        self.auth_url = 'https://accounts.google.com/o/oauth2/v2/auth'
        self._load_config()
    
    def _load_config(self):
        """Load OAuth configuration from environment"""
        import os
        self.client_id = os.getenv('GOOGLE_CLIENT_ID') or os.getenv('GMAIL_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET') or os.getenv('GMAIL_CLIENT_SECRET')
        self.redirect_uri = os.getenv('GMAIL_REDIRECT_URI', 'http://localhost:5000/auth/gmail/callback')
    
    def generate_auth_url(self, user_id: int, state: str = None) -> Dict[str, Any]:
        """Generate Gmail OAuth authorization URL"""
        if not self.client_id:
            return {
                'success': False,
                'error': 'Gmail OAuth not configured',
                'error_code': 'OAUTH_NOT_CONFIGURED'
            }
        
        if not state:
            state = secrets.token_urlsafe(32)
        
        # Store state for verification
        db_optimizer.execute_query(
            """INSERT OR REPLACE INTO system_config (key, value) 
               VALUES (?, ?)""",
            (f"oauth_state_{state}", json.dumps({
                'user_id': user_id,
                'created_at': datetime.now().isoformat()
            })),
            fetch=False
        )
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.scopes),
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent',
            'state': state
        }
        
        auth_url = f"{self.auth_url}?{urlencode(params)}"
        
        return {
            'success': True,
            'auth_url': auth_url,
            'state': state,
            'message': 'Authorization URL generated'
        }
    
    def handle_oauth_callback(self, code: str, state: str) -> Dict[str, Any]:
        """Handle OAuth callback and exchange code for tokens"""
        try:
            # Verify state
            state_data = db_optimizer.execute_query(
                "SELECT value FROM system_config WHERE key = ?",
                (f"oauth_state_{state}",)
            )
            
            if not state_data:
                return {
                    'success': False,
                    'error': 'Invalid or expired state',
                    'error_code': 'INVALID_STATE'
                }
            
            state_info = json.loads(state_data[0]['value'])
            user_id = state_info['user_id']
            
            # Exchange code for tokens
            token_data = self._exchange_code_for_tokens(code)
            
            if not token_data['success']:
                return token_data
            
            # Store tokens in database
            token_result = self._store_tokens(user_id, token_data['tokens'])
            
            if not token_result['success']:
                return token_result
            
            # Clean up state
            db_optimizer.execute_query(
                "DELETE FROM system_config WHERE key = ?",
                (f"oauth_state_{state}",),
                fetch=False
            )
            
            # Update user onboarding step
            user_auth_manager.update_user_profile(
                user_id, 
                onboarding_step=3  # Gmail connected step
            )
            
            # Start onboarding job after successful Gmail connection
            try:
                from core.onboarding_orchestrator import onboarding_orchestrator
                onboarding_result = onboarding_orchestrator.start_onboarding_job(user_id)
                if onboarding_result['success']:
                    logger.info(f"Started onboarding job {onboarding_result['job_id']} for user {user_id}")
                else:
                    logger.warning(f"Failed to start onboarding job for user {user_id}: {onboarding_result['error']}")
            except Exception as e:
                logger.error(f"Error starting onboarding job for user {user_id}: {e}")
                # Don't fail the OAuth callback for onboarding issues
            
            logger.info(f"Gmail OAuth completed for user {user_id}")
            
            return {
                'success': True,
                'user_id': user_id,
                'message': 'Gmail account connected successfully'
            }
            
        except Exception as e:
            logger.error(f"Error handling OAuth callback: {e}")
            return {
                'success': False,
                'error': 'Failed to complete Gmail connection',
                'error_code': 'OAUTH_CALLBACK_ERROR'
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
            
            tokens = response.json()
            
            return {
                'success': True,
                'tokens': tokens
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Token exchange failed: {e}")
            return {
                'success': False,
                'error': 'Failed to exchange code for tokens',
                'error_code': 'TOKEN_EXCHANGE_ERROR'
            }
    
    def _store_tokens(self, user_id: int, tokens: Dict[str, Any]) -> Dict[str, Any]:
        """Store OAuth tokens in database"""
        try:
            # Deactivate existing tokens
            db_optimizer.execute_query(
                "UPDATE gmail_tokens SET is_active = 0 WHERE user_id = ?",
                (user_id,),
                fetch=False
            )
            
            # Calculate expiration time
            expires_at = None
            if 'expires_in' in tokens:
                expires_at = datetime.now() + timedelta(seconds=tokens['expires_in'])
            
            # Store new tokens
            db_optimizer.execute_query(
                """INSERT INTO gmail_tokens 
                   (user_id, access_token, refresh_token, token_type, 
                    expires_at, scope, metadata) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, tokens['access_token'], tokens.get('refresh_token'),
                 tokens.get('token_type', 'Bearer'), expires_at.isoformat() if expires_at else None,
                 ' '.join(self.scopes), json.dumps(tokens)),
                fetch=False
            )
            
            return {
                'success': True,
                'message': 'Tokens stored successfully'
            }
            
        except Exception as e:
            logger.error(f"Error storing tokens: {e}")
            return {
                'success': False,
                'error': 'Failed to store tokens',
                'error_code': 'TOKEN_STORE_ERROR'
            }
    
    def get_user_tokens(self, user_id: int) -> Optional[GmailToken]:
        """Get active Gmail tokens for user"""
        try:
            token_data = db_optimizer.execute_query(
                """SELECT * FROM gmail_tokens 
                   WHERE user_id = ? AND is_active = 1 
                   ORDER BY created_at DESC LIMIT 1""",
                (user_id,)
            )
            
            if not token_data:
                return None
            
            token = token_data[0]
            return GmailToken(
                id=token['id'],
                user_id=token['user_id'],
                access_token=token['access_token'],
                refresh_token=token['refresh_token'],
                token_type=token['token_type'],
                expires_at=datetime.fromisoformat(token['expires_at']) if token['expires_at'] else None,
                scope=token['scope'],
                created_at=datetime.fromisoformat(token['created_at']),
                is_active=bool(token['is_active'])
            )
            
        except Exception as e:
            logger.error(f"Error getting user tokens: {e}")
            return None
    
    def refresh_access_token(self, user_id: int) -> Dict[str, Any]:
        """Refresh expired access token"""
        try:
            token = self.get_user_tokens(user_id)
            
            if not token or not token.refresh_token:
                return {
                    'success': False,
                    'error': 'No refresh token available',
                    'error_code': 'NO_REFRESH_TOKEN'
                }
            
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': token.refresh_token,
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(self.token_url, data=data, timeout=30)
            response.raise_for_status()
            
            new_tokens = response.json()
            
            # Update tokens in database
            expires_at = None
            if 'expires_in' in new_tokens:
                expires_at = datetime.now() + timedelta(seconds=new_tokens['expires_in'])
            
            db_optimizer.execute_query(
                """UPDATE gmail_tokens 
                   SET access_token = ?, expires_at = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (new_tokens['access_token'], 
                 expires_at.isoformat() if expires_at else None,
                 token.id),
                fetch=False
            )
            
            return {
                'success': True,
                'access_token': new_tokens['access_token'],
                'expires_at': expires_at.isoformat() if expires_at else None,
                'message': 'Token refreshed successfully'
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Token refresh failed: {e}")
            return {
                'success': False,
                'error': 'Failed to refresh token',
                'error_code': 'TOKEN_REFRESH_ERROR'
            }
    
    def revoke_gmail_access(self, user_id: int) -> Dict[str, Any]:
        """Revoke Gmail access for user"""
        try:
            # Deactivate tokens
            db_optimizer.execute_query(
                "UPDATE gmail_tokens SET is_active = 0 WHERE user_id = ?",
                (user_id,),
                fetch=False
            )
            
            # Update user onboarding step
            user_auth_manager.update_user_profile(
                user_id,
                onboarding_step=2  # Back to business info step
            )
            
            logger.info(f"Gmail access revoked for user {user_id}")
            
            return {
                'success': True,
                'message': 'Gmail access revoked successfully'
            }
            
        except Exception as e:
            logger.error(f"Error revoking Gmail access: {e}")
            return {
                'success': False,
                'error': 'Failed to revoke Gmail access',
                'error_code': 'REVOKE_ERROR'
            }
    
    def is_gmail_connected(self, user_id: int) -> bool:
        """Check if user has active Gmail connection"""
        token = self.get_user_tokens(user_id)
        return token is not None and token.is_active

class GmailSyncManager:
    """Manages Gmail email synchronization"""
    
    def __init__(self):
        self.oauth_manager = GmailOAuthManager()
        self.gmail_api_base = 'https://gmail.googleapis.com/gmail/v1'
    
    def start_initial_sync(self, user_id: int) -> Dict[str, Any]:
        """Start initial email synchronization"""
        try:
            # Check if Gmail is connected
            if not self.oauth_manager.is_gmail_connected(user_id):
                return {
                    'success': False,
                    'error': 'Gmail not connected',
                    'error_code': 'GMAIL_NOT_CONNECTED'
                }
            
            # Create sync record
            sync_id = db_optimizer.execute_query(
                """INSERT INTO email_sync 
                   (user_id, sync_type, status, metadata) 
                   VALUES (?, ?, ?, ?)""",
                ('initial', 'pending', json.dumps({
                    'started_by': 'user',
                    'sync_range': 'last_90_days'
                })),
                fetch=False
            )
            
            # Start background sync (in production, this would be a background job)
            self._perform_sync(user_id, sync_id)
            
            return {
                'success': True,
                'sync_id': sync_id,
                'message': 'Initial sync started'
            }
            
        except Exception as e:
            logger.error(f"Error starting initial sync: {e}")
            return {
                'success': False,
                'error': 'Failed to start sync',
                'error_code': 'SYNC_START_ERROR'
            }
    
    def _perform_sync(self, user_id: int, sync_id: int):
        """Perform the actual email synchronization"""
        try:
            # Update sync status to running
            db_optimizer.execute_query(
                "UPDATE email_sync SET status = 'running', started_at = CURRENT_TIMESTAMP WHERE id = ?",
                (sync_id,),
                fetch=False
            )
            
            # Get Gmail tokens
            token = self.oauth_manager.get_user_tokens(user_id)
            if not token:
                raise Exception("No valid Gmail tokens")
            
            # Check if token needs refresh
            if token.expires_at and token.expires_at < datetime.now():
                refresh_result = self.oauth_manager.refresh_access_token(user_id)
                if not refresh_result['success']:
                    raise Exception("Failed to refresh token")
                token = self.oauth_manager.get_user_tokens(user_id)
            
            # Fetch emails from Gmail API
            emails = self._fetch_emails_from_gmail(token.access_token)
            
            # Process and store emails
            processed_count = self._process_emails(user_id, emails)
            
            # Update sync status
            db_optimizer.execute_query(
                """UPDATE email_sync 
                   SET status = 'completed', emails_processed = ?, emails_total = ?, 
                       completed_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (processed_count, len(emails), sync_id),
                fetch=False
            )
            
            logger.info(f"Sync completed for user {user_id}: {processed_count} emails processed")
            
        except Exception as e:
            logger.error(f"Sync failed for user {user_id}: {e}")
            
            # Update sync status to failed
            db_optimizer.execute_query(
                """UPDATE email_sync 
                   SET status = 'failed', error_message = ?, completed_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (str(e), sync_id),
                fetch=False
            )
    
    def _fetch_emails_from_gmail(self, access_token: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """Fetch emails from Gmail API"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            # Get message list
            response = requests.get(
                f"{self.gmail_api_base}/users/me/messages",
                headers=headers,
                params={'maxResults': max_results},
                timeout=30
            )
            response.raise_for_status()
            
            messages = response.json().get('messages', [])
            
            # Fetch full message details
            emails = []
            for message in messages[:50]:  # Limit to 50 for initial sync
                try:
                    msg_response = requests.get(
                        f"{self.gmail_api_base}/users/me/messages/{message['id']}",
                        headers=headers,
                        timeout=30
                    )
                    msg_response.raise_for_status()
                    emails.append(msg_response.json())
                except Exception as e:
                    logger.warning(f"Failed to fetch message {message['id']}: {e}")
                    continue
            
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails from Gmail: {e}")
            return []
    
    def _process_emails(self, user_id: int, emails: List[Dict[str, Any]]) -> int:
        """Process and store emails in CRM"""
        processed_count = 0
        
        for email in emails:
            try:
                # Extract email data
                email_data = self._extract_email_data(email)
                
                if not email_data:
                    continue
                
                # Check if lead already exists
                existing_lead = db_optimizer.execute_query(
                    "SELECT id FROM leads WHERE user_id = ? AND email = ?",
                    (user_id, email_data['email'])
                )
                
                if not existing_lead:
                    # Create new lead
                    db_optimizer.execute_query(
                        """INSERT INTO leads 
                           (user_id, email, name, company, source, metadata) 
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (user_id, email_data['email'], email_data['name'],
                         email_data.get('company'), 'gmail', json.dumps(email_data)),
                        fetch=False
                    )
                    
                    processed_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to process email: {e}")
                continue
        
        return processed_count
    
    def _extract_email_data(self, email: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract relevant data from Gmail email"""
        try:
            payload = email.get('payload', {})
            headers = payload.get('headers', [])
            
            # Extract header values
            header_map = {}
            for header in headers:
                header_map[header['name'].lower()] = header['value']
            
            # Extract basic info
            sender_email = header_map.get('from', '')
            subject = header_map.get('subject', '')
            date = header_map.get('date', '')
            
            # Parse sender name and email
            if '<' in sender_email and '>' in sender_email:
                name = sender_email.split('<')[0].strip().strip('"')
                email_addr = sender_email.split('<')[1].split('>')[0].strip()
            else:
                name = sender_email
                email_addr = sender_email
            
            return {
                'email': email_addr,
                'name': name,
                'subject': subject,
                'date': date,
                'gmail_id': email['id'],
                'thread_id': email.get('threadId')
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract email data: {e}")
            return None
    
    def get_sync_status(self, user_id: int) -> Optional[EmailSyncStatus]:
        """Get current sync status for user"""
        try:
            sync_data = db_optimizer.execute_query(
                """SELECT * FROM email_sync 
                   WHERE user_id = ? 
                   ORDER BY started_at DESC LIMIT 1""",
                (user_id,)
            )
            
            if not sync_data:
                return None
            
            sync = sync_data[0]
            return EmailSyncStatus(
                id=sync['id'],
                user_id=sync['user_id'],
                sync_type=sync['sync_type'],
                status=sync['status'],
                emails_processed=sync['emails_processed'],
                emails_total=sync['emails_total'],
                started_at=datetime.fromisoformat(sync['started_at']),
                completed_at=datetime.fromisoformat(sync['completed_at']) if sync['completed_at'] else None,
                error_message=sync['error_message'],
                metadata=json.loads(sync['metadata'] or '{}')
            )
            
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return None

# Global instances
gmail_oauth_manager = GmailOAuthManager()
gmail_sync_manager = GmailSyncManager()

# Export the Gmail integration system
__all__ = [
    'GmailOAuthManager', 'gmail_oauth_manager',
    'GmailSyncManager', 'gmail_sync_manager',
    'GmailToken', 'EmailSyncStatus'
]
