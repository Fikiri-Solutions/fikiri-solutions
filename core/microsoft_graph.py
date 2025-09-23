"""
Microsoft Graph API Integration for Fikiri Solutions
Handles authentication and API calls to Microsoft 365 services
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests
from msal import ConfidentialClientApplication, PublicClientApplication
import time

logger = logging.getLogger(__name__)

@dataclass
class MicrosoftUser:
    """Microsoft user profile data"""
    id: str
    email: str
    display_name: str
    given_name: Optional[str] = None
    surname: Optional[str] = None
    job_title: Optional[str] = None
    office_location: Optional[str] = None

@dataclass
class MicrosoftEmail:
    """Microsoft email message data"""
    id: str
    subject: str
    sender: str
    received_time: str
    body_preview: str
    is_read: bool
    importance: str
    has_attachments: bool

class MicrosoftGraphConfig:
    """Configuration for Microsoft Graph API"""
    
    def __init__(self):
        self.client_id = os.getenv('MICROSOFT_CLIENT_ID')
        self.client_secret = os.getenv('MICROSOFT_CLIENT_SECRET')
        self.tenant_id = os.getenv('MICROSOFT_TENANT_ID')
        self.redirect_uri = os.getenv('MICROSOFT_REDIRECT_URI', 'http://localhost:5000/auth/microsoft/callback')
        
        # Graph API endpoints
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"
        
        # Scopes for different operations
        self.scopes = {
            'user_read': ['User.Read'],
            'mail_read': ['Mail.Read'],
            'mail_send': ['Mail.Send'],
            'calendar_read': ['Calendars.Read'],
            'calendar_write': ['Calendars.ReadWrite'],
            'contacts_read': ['Contacts.Read'],
            'offline_access': ['offline_access']
        }
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate that required configuration is present"""
        required_vars = ['client_id', 'client_secret', 'tenant_id']
        missing_vars = [var for var in required_vars if not getattr(self, var)]
        
        if missing_vars:
            logger.warning(f"Missing Microsoft Graph configuration: {missing_vars}")
            logger.warning("Microsoft Graph features will be disabled")

class MicrosoftGraphClient:
    """Microsoft Graph API client for Fikiri Solutions"""
    
    def __init__(self, config: MicrosoftGraphConfig):
        self.config = config
        self.app = None
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = 0
        
        if self.config.client_id and self.config.client_secret:
            self._initialize_app()
    
    def _initialize_app(self):
        """Initialize MSAL application"""
        try:
            self.app = ConfidentialClientApplication(
                client_id=self.config.client_id,
                client_credential=self.config.client_secret,
                authority=self.config.authority
            )
            logger.info("Microsoft Graph client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Microsoft Graph client: {e}")
            self.app = None
    
    def get_auth_url(self, scopes: List[str] = None) -> Optional[str]:
        """Generate Microsoft authentication URL"""
        if not self.app:
            return None
        
        try:
            scopes = scopes or self.config.scopes['user_read']
            auth_url = self.app.get_authorization_request_url(
                scopes=scopes,
                redirect_uri=self.config.redirect_uri
            )
            return auth_url
        except Exception as e:
            logger.error(f"Failed to generate auth URL: {e}")
            return None
    
    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        if not self.app:
            return {'success': False, 'error': 'Microsoft Graph not configured'}
        
        try:
            result = self.app.acquire_token_by_authorization_code(
                code=code,
                scopes=self.config.scopes['user_read'] + self.config.scopes['mail_read'],
                redirect_uri=self.config.redirect_uri
            )
            
            if 'access_token' in result:
                self.access_token = result['access_token']
                self.refresh_token = result.get('refresh_token')
                self.token_expires_at = time.time() + result.get('expires_in', 3600)
                
                logger.info("Successfully acquired Microsoft Graph access token")
                return {
                    'success': True,
                    'access_token': self.access_token,
                    'refresh_token': self.refresh_token,
                    'expires_in': result.get('expires_in', 3600)
                }
            else:
                logger.error(f"Token acquisition failed: {result.get('error_description', 'Unknown error')}")
                return {
                    'success': False,
                    'error': result.get('error_description', 'Token acquisition failed')
                }
        except Exception as e:
            logger.error(f"Error exchanging code for token: {e}")
            return {'success': False, 'error': str(e)}
    
    def _make_request(self, endpoint: str, method: str = 'GET', data: Dict = None) -> Dict[str, Any]:
        """Make authenticated request to Microsoft Graph API"""
        if not self.access_token or time.time() >= self.token_expires_at:
            if not self._refresh_token():
                return {'success': False, 'error': 'No valid access token'}
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.config.graph_endpoint}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method == 'PATCH':
                response = requests.patch(url, headers=headers, json=data)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                return {'success': False, 'error': f'Unsupported method: {method}'}
            
            response.raise_for_status()
            return {'success': True, 'data': response.json()}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Graph API request failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _refresh_token(self) -> bool:
        """Refresh access token using refresh token"""
        if not self.refresh_token or not self.app:
            return False
        
        try:
            result = self.app.acquire_token_by_refresh_token(
                refresh_token=self.refresh_token,
                scopes=self.config.scopes['user_read'] + self.config.scopes['mail_read']
            )
            
            if 'access_token' in result:
                self.access_token = result['access_token']
                self.refresh_token = result.get('refresh_token')
                self.token_expires_at = time.time() + result.get('expires_in', 3600)
                return True
            else:
                logger.error(f"Token refresh failed: {result.get('error_description', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return False
    
    def get_user_profile(self) -> Dict[str, Any]:
        """Get current user profile"""
        result = self._make_request('/me')
        if result['success']:
            user_data = result['data']
            return {
                'success': True,
                'user': MicrosoftUser(
                    id=user_data.get('id'),
                    email=user_data.get('mail') or user_data.get('userPrincipalName'),
                    display_name=user_data.get('displayName'),
                    given_name=user_data.get('givenName'),
                    surname=user_data.get('surname'),
                    job_title=user_data.get('jobTitle'),
                    office_location=user_data.get('officeLocation')
                )
            }
        return result
    
    def get_emails(self, folder: str = 'inbox', limit: int = 50) -> Dict[str, Any]:
        """Get user's emails from specified folder"""
        endpoint = f'/me/mailFolders/{folder}/messages'
        params = f'?$top={limit}&$orderby=receivedDateTime desc'
        
        result = self._make_request(f'{endpoint}{params}')
        if result['success']:
            emails = []
            for email_data in result['data'].get('value', []):
                emails.append(MicrosoftEmail(
                    id=email_data.get('id'),
                    subject=email_data.get('subject', 'No Subject'),
                    sender=email_data.get('from', {}).get('emailAddress', {}).get('address', 'Unknown'),
                    received_time=email_data.get('receivedDateTime'),
                    body_preview=email_data.get('bodyPreview', ''),
                    is_read=email_data.get('isRead', False),
                    importance=email_data.get('importance', 'normal'),
                    has_attachments=email_data.get('hasAttachments', False)
                ))
            
            return {'success': True, 'emails': emails}
        return result
    
    def send_email(self, to: str, subject: str, body: str, is_html: bool = True) -> Dict[str, Any]:
        """Send email via Microsoft Graph"""
        email_data = {
            'message': {
                'subject': subject,
                'body': {
                    'contentType': 'HTML' if is_html else 'Text',
                    'content': body
                },
                'toRecipients': [
                    {
                        'emailAddress': {
                            'address': to
                        }
                    }
                ]
            },
            'saveToSentItems': True
        }
        
        return self._make_request('/me/sendMail', method='POST', data=email_data)
    
    def get_calendar_events(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Get calendar events"""
        endpoint = '/me/events'
        params = []
        
        if start_date:
            params.append(f"startDateTime={start_date}")
        if end_date:
            params.append(f"endDateTime={end_date}")
        
        if params:
            endpoint += '?' + '&'.join(params)
        
        return self._make_request(endpoint)
    
    def create_calendar_event(self, subject: str, start_time: str, end_time: str, 
                            attendees: List[str] = None, body: str = None) -> Dict[str, Any]:
        """Create calendar event"""
        event_data = {
            'subject': subject,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC'
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC'
            }
        }
        
        if attendees:
            event_data['attendees'] = [
                {'emailAddress': {'address': email}} for email in attendees
            ]
        
        if body:
            event_data['body'] = {
                'contentType': 'HTML',
                'content': body
            }
        
        return self._make_request('/me/events', method='POST', data=event_data)

class MicrosoftGraphService:
    """Service layer for Microsoft Graph operations in Fikiri"""
    
    def __init__(self):
        self.config = MicrosoftGraphConfig()
        self.client = MicrosoftGraphClient(self.config)
    
    def is_configured(self) -> bool:
        """Check if Microsoft Graph is properly configured"""
        return self.client.app is not None
    
    def get_auth_url(self) -> Optional[str]:
        """Get Microsoft authentication URL"""
        return self.client.get_auth_url()
    
    def authenticate_user(self, code: str) -> Dict[str, Any]:
        """Authenticate user with Microsoft"""
        return self.client.exchange_code_for_token(code)
    
    def get_user_info(self) -> Dict[str, Any]:
        """Get authenticated user information"""
        return self.client.get_user_profile()
    
    def get_user_emails(self, limit: int = 50) -> Dict[str, Any]:
        """Get user's emails"""
        return self.client.get_emails(limit=limit)
    
    def send_user_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Send email on behalf of user"""
        return self.client.send_email(to, subject, body)
    
    def get_user_calendar(self, days_ahead: int = 7) -> Dict[str, Any]:
        """Get user's calendar events"""
        from datetime import datetime, timedelta
        
        start_date = datetime.utcnow().isoformat() + 'Z'
        end_date = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'
        
        return self.client.get_calendar_events(start_date, end_date)
    
    def create_calendar_event(self, subject: str, start_time: str, end_time: str, 
                            attendees: List[str] = None, body: str = None) -> Dict[str, Any]:
        """Create calendar event for user"""
        return self.client.create_calendar_event(subject, start_time, end_time, attendees, body)

# Global instance
microsoft_graph_service = MicrosoftGraphService()

