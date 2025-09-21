#!/usr/bin/env python3
"""
Microsoft Graph API Integration for Fikiri Solutions
Enhanced email service provider for Microsoft 365/Outlook
"""

import os
import json
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class MicrosoftGraphProvider:
    """Microsoft Graph API provider for Office 365/Outlook integration."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.service_name = "Microsoft 365"
        self.authenticated = False
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        
        # Microsoft Graph API endpoints
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.auth_url = "https://login.microsoftonline.com"
        
        # OAuth 2.0 configuration
        self.client_id = config.get('client_id')
        self.client_secret = config.get('client_secret')
        self.tenant_id = config.get('tenant_id')
        self.redirect_uri = config.get('redirect_uri')
        self.scope = "https://graph.microsoft.com/Mail.ReadWrite https://graph.microsoft.com/Calendars.ReadWrite https://graph.microsoft.com/Contacts.ReadWrite"
    
    def get_auth_url(self, state: str = None) -> str:
        """Generate Microsoft OAuth 2.0 authorization URL."""
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': self.scope,
            'response_mode': 'query',
            'state': state or 'microsoft_auth'
        }
        
        auth_url = f"{self.auth_url}/{self.tenant_id}/oauth2/v2.0/authorize"
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{auth_url}?{query_string}"
    
    def exchange_code_for_token(self, code: str) -> bool:
        """Exchange authorization code for access token."""
        token_url = f"{self.auth_url}/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code',
            'scope': self.scope
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.refresh_token = token_data.get('refresh_token')
            self.token_expires_at = datetime.now() + timedelta(seconds=token_data['expires_in'])
            self.authenticated = True
            
            print("✅ Microsoft Graph authentication successful")
            return True
            
        except Exception as e:
            print(f"❌ Microsoft Graph authentication failed: {e}")
            return False
    
    def refresh_access_token(self) -> bool:
        """Refresh expired access token."""
        if not self.refresh_token:
            return False
        
        token_url = f"{self.auth_url}/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token',
            'scope': self.scope
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.refresh_token = token_data.get('refresh_token', self.refresh_token)
            self.token_expires_at = datetime.now() + timedelta(seconds=token_data['expires_in'])
            
            print("✅ Microsoft Graph token refreshed")
            return True
            
        except Exception as e:
            print(f"❌ Microsoft Graph token refresh failed: {e}")
            return False
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for Microsoft Graph API requests."""
        if not self.access_token:
            return {}
        
        # Check if token needs refresh
        if self.token_expires_at and datetime.now() >= self.token_expires_at - timedelta(minutes=5):
            self.refresh_access_token()
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def authenticate(self) -> bool:
        """Authenticate with Microsoft Graph API."""
        # Check if we have stored tokens
        stored_tokens = self.config.get('stored_tokens')
        if stored_tokens:
            self.access_token = stored_tokens.get('access_token')
            self.refresh_token = stored_tokens.get('refresh_token')
            expires_at = stored_tokens.get('expires_at')
            if expires_at:
                self.token_expires_at = datetime.fromisoformat(expires_at)
            
            # Test if token is still valid
            if self.test_connection():
                self.authenticated = True
                return True
            
            # Try to refresh token
            if self.refresh_access_token():
                self.authenticated = True
                return True
        
        return False
    
    def test_connection(self) -> bool:
        """Test connection to Microsoft Graph API."""
        try:
            headers = self.get_headers()
            if not headers:
                return False
            
            response = requests.get(f"{self.base_url}/me", headers=headers)
            return response.status_code == 200
            
        except Exception as e:
            print(f"❌ Microsoft Graph connection test failed: {e}")
            return False
    
    def get_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages from Microsoft Graph API."""
        if not self.authenticated:
            return []
        
        try:
            headers = self.get_headers()
            if not headers:
                return []
            
            # Get messages from inbox
            url = f"{self.base_url}/me/mailFolders/inbox/messages"
            params = {
                '$top': limit,
                '$orderby': 'receivedDateTime desc',
                '$select': 'id,subject,from,receivedDateTime,bodyPreview,isRead,hasAttachments'
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            messages = []
            
            for msg in data.get('value', []):
                message = {
                    'id': msg['id'],
                    'subject': msg.get('subject', 'No Subject'),
                    'from': msg.get('from', {}).get('emailAddress', {}).get('address', 'Unknown'),
                    'from_name': msg.get('from', {}).get('emailAddress', {}).get('name', 'Unknown'),
                    'received_date': msg.get('receivedDateTime'),
                    'body_preview': msg.get('bodyPreview', ''),
                    'is_read': msg.get('isRead', False),
                    'has_attachments': msg.get('hasAttachments', False),
                    'provider': 'microsoft365'
                }
                messages.append(message)
            
            print(f"✅ Retrieved {len(messages)} messages from Microsoft Graph")
            return messages
            
        except Exception as e:
            print(f"❌ Failed to get Microsoft Graph messages: {e}")
            return []
    
    def send_message(self, to: str, subject: str, body: str) -> bool:
        """Send a message via Microsoft Graph API."""
        if not self.authenticated:
            return False
        
        try:
            headers = self.get_headers()
            if not headers:
                return False
            
            # Create message payload
            message = {
                'message': {
                    'subject': subject,
                    'body': {
                        'contentType': 'HTML',
                        'content': body
                    },
                    'toRecipients': [
                        {
                            'emailAddress': {
                                'address': to
                            }
                        }
                    ]
                }
            }
            
            url = f"{self.base_url}/me/sendMail"
            response = requests.post(url, headers=headers, json=message)
            response.raise_for_status()
            
            print(f"✅ Message sent via Microsoft Graph to {to}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send Microsoft Graph message: {e}")
            return False
    
    def get_calendar_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get calendar events from Microsoft Graph API."""
        if not self.authenticated:
            return []
        
        try:
            headers = self.get_headers()
            if not headers:
                return []
            
            # Get upcoming events
            url = f"{self.base_url}/me/events"
            params = {
                '$top': limit,
                '$orderby': 'start/dateTime asc',
                '$select': 'id,subject,start,end,location,attendees'
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            events = []
            
            for event in data.get('value', []):
                event_data = {
                    'id': event['id'],
                    'subject': event.get('subject', 'No Subject'),
                    'start': event.get('start', {}).get('dateTime'),
                    'end': event.get('end', {}).get('dateTime'),
                    'location': event.get('location', {}).get('displayName', ''),
                    'attendees': [att.get('emailAddress', {}).get('address', '') for att in event.get('attendees', [])],
                    'provider': 'microsoft365'
                }
                events.append(event_data)
            
            print(f"✅ Retrieved {len(events)} calendar events from Microsoft Graph")
            return events
            
        except Exception as e:
            print(f"❌ Failed to get Microsoft Graph calendar events: {e}")
            return []
    
    def get_contacts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get contacts from Microsoft Graph API."""
        if not self.authenticated:
            return []
        
        try:
            headers = self.get_headers()
            if not headers:
                return []
            
            # Get contacts
            url = f"{self.base_url}/me/contacts"
            params = {
                '$top': limit,
                '$orderby': 'displayName asc',
                '$select': 'id,displayName,emailAddresses,phoneNumbers'
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            contacts = []
            
            for contact in data.get('value', []):
                contact_data = {
                    'id': contact['id'],
                    'name': contact.get('displayName', 'Unknown'),
                    'email': contact.get('emailAddresses', [{}])[0].get('address', '') if contact.get('emailAddresses') else '',
                    'phone': contact.get('phoneNumbers', [{}])[0].get('number', '') if contact.get('phoneNumbers') else '',
                    'provider': 'microsoft365'
                }
                contacts.append(contact_data)
            
            print(f"✅ Retrieved {len(contacts)} contacts from Microsoft Graph")
            return contacts
            
        except Exception as e:
            print(f"❌ Failed to get Microsoft Graph contacts: {e}")
            return []
    
    def create_calendar_event(self, subject: str, start_time: str, end_time: str, 
                            attendees: List[str] = None, location: str = None) -> bool:
        """Create a calendar event via Microsoft Graph API."""
        if not self.authenticated:
            return False
        
        try:
            headers = self.get_headers()
            if not headers:
                return False
            
            # Create event payload
            event = {
                'subject': subject,
                'start': {
                    'dateTime': start_time,
                    'timeZone': 'UTC'
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': 'UTC'
                },
                'body': {
                    'contentType': 'HTML',
                    'content': f'Event created by Fikiri Solutions'
                }
            }
            
            if attendees:
                event['attendees'] = [
                    {'emailAddress': {'address': email}} for email in attendees
                ]
            
            if location:
                event['location'] = {'displayName': location}
            
            url = f"{self.base_url}/me/events"
            response = requests.post(url, headers=headers, json=event)
            response.raise_for_status()
            
            print(f"✅ Calendar event created via Microsoft Graph: {subject}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create Microsoft Graph calendar event: {e}")
            return False
    
    def get_user_info(self) -> Dict[str, Any]:
        """Get user information from Microsoft Graph API."""
        if not self.authenticated:
            return {}
        
        try:
            headers = self.get_headers()
            if not headers:
                return {}
            
            response = requests.get(f"{self.base_url}/me", headers=headers)
            response.raise_for_status()
            
            user_data = response.json()
            return {
                'id': user_data.get('id'),
                'display_name': user_data.get('displayName'),
                'email': user_data.get('mail') or user_data.get('userPrincipalName'),
                'job_title': user_data.get('jobTitle'),
                'department': user_data.get('department'),
                'company': user_data.get('companyName'),
                'provider': 'microsoft365'
            }
            
        except Exception as e:
            print(f"❌ Failed to get Microsoft Graph user info: {e}")
            return {}
    
    def is_authenticated(self) -> bool:
        """Check if the service is authenticated."""
        return self.authenticated
    
    def get_service_capabilities(self) -> Dict[str, Any]:
        """Get service capabilities."""
        return {
            'email_management': True,
            'calendar_integration': True,
            'contact_management': True,
            'file_storage': True,
            'teams_integration': True,
            'security_features': ['encryption', '2fa', 'audit_logs', 'compliance'],
            'api_type': 'REST',
            'oauth_version': '2.0',
            'rate_limits': '10000 requests per 10 minutes'
        }

# Configuration template for Microsoft Graph API
MICROSOFT_GRAPH_CONFIG_TEMPLATE = {
    'client_id': 'your_microsoft_client_id',
    'client_secret': 'your_microsoft_client_secret',
    'tenant_id': 'your_azure_tenant_id',
    'redirect_uri': 'https://fikirisolutions.com/auth/microsoft/callback',
    'stored_tokens': {
        'access_token': None,
        'refresh_token': None,
        'expires_at': None
    }
}

if __name__ == "__main__":
    # Test Microsoft Graph provider
    config = {
        'client_id': os.getenv('MICROSOFT_CLIENT_ID'),
        'client_secret': os.getenv('MICROSOFT_CLIENT_SECRET'),
        'tenant_id': os.getenv('MICROSOFT_TENANT_ID'),
        'redirect_uri': os.getenv('MICROSOFT_REDIRECT_URI'),
        'stored_tokens': {}
    }
    
    provider = MicrosoftGraphProvider(config)
    
    # Test authentication
    if provider.authenticate():
        print("✅ Microsoft Graph provider authenticated successfully")
        
        # Test getting user info
        user_info = provider.get_user_info()
        print(f"User: {user_info.get('display_name')} ({user_info.get('email')})")
        
        # Test getting messages
        messages = provider.get_messages(5)
        print(f"Retrieved {len(messages)} messages")
        
        # Test getting calendar events
        events = provider.get_calendar_events(5)
        print(f"Retrieved {len(events)} calendar events")
        
        # Test getting contacts
        contacts = provider.get_contacts(5)
        print(f"Retrieved {len(contacts)} contacts")
        
    else:
        print("❌ Microsoft Graph provider authentication failed")
        print("Please check your configuration and try again")
