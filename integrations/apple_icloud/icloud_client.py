#!/usr/bin/env python3
"""
Apple iCloud Mail Integration for Fikiri Solutions
iCloud Mail API integration using CloudKit
"""

import os
import json
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import base64

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    jwt = None

class AppleiCloudProvider:
    """Apple iCloud Mail provider using CloudKit API."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.service_name = "Apple iCloud Mail"
        self.authenticated = False
        
        # Apple CloudKit configuration
        self.team_id = config.get('team_id')
        self.key_id = config.get('key_id')
        self.private_key = config.get('private_key')
        self.bundle_id = config.get('bundle_id')
        
        # CloudKit API endpoints
        self.base_url = f"https://api.apple-cloudkit.com/database/1/{self.team_id}/{self.bundle_id}"
        self.auth_token = None
        self.token_expires_at = None
    
    def generate_jwt_token(self) -> str:
        """Generate JWT token for CloudKit authentication."""
        try:
            # Prepare JWT payload
            now = int(time.time())
            payload = {
                'iss': self.team_id,
                'iat': now,
                'exp': now + 3600,  # 1 hour expiration
                'aud': 'https://api.apple-cloudkit.com'
            }
            
            # Load private key
            private_key = self.private_key
            if not private_key.startswith('-----BEGIN'):
                # Assume it's base64 encoded
                private_key = base64.b64decode(private_key).decode('utf-8')
            
            # Generate JWT token
            token = jwt.encode(
                payload,
                private_key,
                algorithm='ES256',
                headers={'kid': self.key_id}
            )
            
            return token
            
        except Exception as e:
            logger.error("Failed to generate Apple JWT token: %s", e)
            return None
    
    def authenticate(self) -> bool:
        """Authenticate with Apple CloudKit API."""
        if not all([self.team_id, self.key_id, self.private_key, self.bundle_id]):
            return False
        
        try:
            # Generate JWT token
            self.auth_token = self.generate_jwt_token()
            if not self.auth_token:
                return False
            
            # Test API connection
            headers = {
                'Authorization': f'Bearer {self.auth_token}',
                'Content-Type': 'application/json'
            }
            
            # Test with a simple query
            response = requests.post(
                f"{self.base_url}/public/records/query",
                headers=headers,
                json={
                    'query': {
                        'recordType': 'MailMessage',
                        'filterBy': [],
                        'sortBy': []
                    }
                }
            )
            
            if response.status_code == 200:
                self.authenticated = True
                self.token_expires_at = datetime.now() + timedelta(hours=1)
                logger.info(" Apple iCloud Mail authentication successful")
                return True
            else:
                logger.error(" Apple iCloud Mail authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error("Apple iCloud Mail authentication error: %s", e)
            return False
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for CloudKit API requests."""
        if not self.auth_token:
            return {}
        
        # Check if token needs refresh
        if self.token_expires_at and datetime.now() >= self.token_expires_at - timedelta(minutes=5):
            self.auth_token = self.generate_jwt_token()
        
        return {
            'Authorization': f'Bearer {self.auth_token}',
            'Content-Type': 'application/json'
        }
    
    def get_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages from iCloud Mail."""
        if not self.authenticated:
            return []
        
        try:
            headers = self.get_headers()
            if not headers:
                return []
            
            # Query CloudKit for mail messages
            query_data = {
                'query': {
                    'recordType': 'MailMessage',
                    'filterBy': [],
                    'sortBy': [
                        {
                            'fieldName': 'receivedDate',
                            'ascending': False
                        }
                    ],
                    'resultsLimit': limit
                }
            }
            
            response = requests.post(
                f"{self.base_url}/public/records/query",
                headers=headers,
                json=query_data
            )
            response.raise_for_status()
            
            data = response.json()
            messages = []
            
            for record in data.get('records', []):
                fields = record.get('fields', {})
                message = {
                    'id': record.get('recordName'),
                    'subject': fields.get('subject', {}).get('value', 'No Subject'),
                    'from': fields.get('from', {}).get('value', 'Unknown'),
                    'received_date': fields.get('receivedDate', {}).get('value'),
                    'body_preview': fields.get('bodyPreview', {}).get('value', ''),
                    'is_read': fields.get('isRead', {}).get('value', False),
                    'has_attachments': fields.get('hasAttachments', {}).get('value', False),
                    'provider': 'icloud'
                }
                messages.append(message)
            
            logger.info("Retrieved %s messages from Apple iCloud", len(messages))
            return messages
            
        except Exception as e:
            logger.error("Failed to get Apple iCloud messages: %s", e)
            return []
    
    def send_message(self, to: str, subject: str, body: str) -> bool:
        """Send a message via iCloud Mail."""
        if not self.authenticated:
            return False
        
        try:
            headers = self.get_headers()
            if not headers:
                return False
            
            # Create mail message record
            message_record = {
                'recordType': 'MailMessage',
                'fields': {
                    'to': {'value': to},
                    'subject': {'value': subject},
                    'body': {'value': body},
                    'sentDate': {'value': datetime.now().isoformat()},
                    'isRead': {'value': False}
                }
            }
            
            response = requests.post(
                f"{self.base_url}/public/records/modify",
                headers=headers,
                json={
                    'operations': [
                        {
                            'operationType': 'create',
                            'record': message_record
                        }
                    ]
                }
            )
            response.raise_for_status()
            
            logger.info("Message sent via Apple iCloud to %s", to)
            return True
            
        except Exception as e:
            logger.error("Failed to send Apple iCloud message: %s", e)
            return False
    
    def get_contacts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get contacts from iCloud."""
        if not self.authenticated:
            return []
        
        try:
            headers = self.get_headers()
            if not headers:
                return []
            
            # Query CloudKit for contacts
            query_data = {
                'query': {
                    'recordType': 'Contact',
                    'filterBy': [],
                    'sortBy': [
                        {
                            'fieldName': 'displayName',
                            'ascending': True
                        }
                    ],
                    'resultsLimit': limit
                }
            }
            
            response = requests.post(
                f"{self.base_url}/public/records/query",
                headers=headers,
                json=query_data
            )
            response.raise_for_status()
            
            data = response.json()
            contacts = []
            
            for record in data.get('records', []):
                fields = record.get('fields', {})
                contact = {
                    'id': record.get('recordName'),
                    'name': fields.get('displayName', {}).get('value', 'Unknown'),
                    'email': fields.get('email', {}).get('value', ''),
                    'phone': fields.get('phone', {}).get('value', ''),
                    'provider': 'icloud'
                }
                contacts.append(contact)
            
            logger.info("Retrieved %s contacts from Apple iCloud", len(contacts))
            return contacts
            
        except Exception as e:
            logger.error("Failed to get Apple iCloud contacts: %s", e)
            return []
    
    def get_calendar_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get calendar events from iCloud."""
        if not self.authenticated:
            return []
        
        try:
            headers = self.get_headers()
            if not headers:
                return []
            
            # Query CloudKit for calendar events
            query_data = {
                'query': {
                    'recordType': 'CalendarEvent',
                    'filterBy': [],
                    'sortBy': [
                        {
                            'fieldName': 'startDate',
                            'ascending': True
                        }
                    ],
                    'resultsLimit': limit
                }
            }
            
            response = requests.post(
                f"{self.base_url}/public/records/query",
                headers=headers,
                json=query_data
            )
            response.raise_for_status()
            
            data = response.json()
            events = []
            
            for record in data.get('records', []):
                fields = record.get('fields', {})
                event = {
                    'id': record.get('recordName'),
                    'subject': fields.get('title', {}).get('value', 'No Subject'),
                    'start': fields.get('startDate', {}).get('value'),
                    'end': fields.get('endDate', {}).get('value'),
                    'location': fields.get('location', {}).get('value', ''),
                    'attendees': fields.get('attendees', {}).get('value', []),
                    'provider': 'icloud'
                }
                events.append(event)
            
            logger.info("Retrieved %s calendar events from Apple iCloud", len(events))
            return events
            
        except Exception as e:
            logger.error("Failed to get Apple iCloud calendar events: %s", e)
            return []
    
    def create_calendar_event(self, subject: str, start_time: str, end_time: str,
                            attendees: List[str] = None, location: str = None) -> bool:
        """Create a calendar event in iCloud."""
        if not self.authenticated:
            return False
        
        try:
            headers = self.get_headers()
            if not headers:
                return False
            
            # Create calendar event record
            event_record = {
                'recordType': 'CalendarEvent',
                'fields': {
                    'title': {'value': subject},
                    'startDate': {'value': start_time},
                    'endDate': {'value': end_time},
                    'location': {'value': location or ''},
                    'attendees': {'value': attendees or []},
                    'createdDate': {'value': datetime.now().isoformat()}
                }
            }
            
            response = requests.post(
                f"{self.base_url}/public/records/modify",
                headers=headers,
                json={
                    'operations': [
                        {
                            'operationType': 'create',
                            'record': event_record
                        }
                    ]
                }
            )
            response.raise_for_status()
            
            logger.info("Calendar event created via Apple iCloud: %s", subject)
            return True
            
        except Exception as e:
            logger.error("Failed to create Apple iCloud calendar event: %s", e)
            return False
    
    def get_user_info(self) -> Dict[str, Any]:
        """Get user information from iCloud."""
        if not self.authenticated:
            return {}
        
        try:
            headers = self.get_headers()
            if not headers:
                return {}
            
            # Get user info from CloudKit
            response = requests.get(f"{self.base_url}/public/users/current", headers=headers)
            response.raise_for_status()
            
            user_data = response.json()
            return {
                'id': user_data.get('userRecordName'),
                'display_name': user_data.get('displayName'),
                'email': user_data.get('email'),
                'provider': 'icloud'
            }
            
        except Exception as e:
            logger.error("Failed to get Apple iCloud user info: %s", e)
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
            'security_features': ['encryption', '2fa', 'privacy'],
            'api_type': 'CloudKit',
            'oauth_version': 'JWT',
            'rate_limits': '1000 requests per hour'
        }

# Configuration template for Apple iCloud API
APPLE_ICLOUD_CONFIG_TEMPLATE = {
    'team_id': 'your_apple_team_id',
    'key_id': 'your_apple_key_id',
    'private_key': 'your_apple_private_key',
    'bundle_id': 'com.fikirisolutions.app'
}

if __name__ == "__main__":
    # Test Apple iCloud provider
    config = {
        'team_id': os.getenv('APPLE_TEAM_ID'),
        'key_id': os.getenv('APPLE_KEY_ID'),
        'private_key': os.getenv('APPLE_PRIVATE_KEY'),
        'bundle_id': os.getenv('APPLE_BUNDLE_ID')
    }
    
    provider = AppleiCloudProvider(config)
    
    # Test authentication
    if provider.authenticate():
        logger.info("Apple iCloud provider authenticated successfully")
        user_info = provider.get_user_info()
        logger.info("User: %s (%s)", user_info.get('display_name'), user_info.get('email'))
        messages = provider.get_messages(5)
        logger.info("Retrieved %s messages", len(messages))
        events = provider.get_calendar_events(5)
        logger.info("Retrieved %s calendar events", len(events))
        contacts = provider.get_contacts(5)
        logger.info("Retrieved %s contacts", len(contacts))
    else:
        logger.error("Apple iCloud provider authentication failed. Check configuration and try again.")
