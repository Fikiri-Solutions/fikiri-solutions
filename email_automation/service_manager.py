#!/usr/bin/env python3
"""
Fikiri Solutions - Email Service Integration Framework
Supports Gmail, Outlook, Yahoo, and generic IMAP/SMTP providers.
"""

import os
import json
import logging
import imaplib
import smtplib
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64

logger = logging.getLogger(__name__)

class EmailServiceProvider:
    """Base class for email service providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.authenticated = False
        self.service_name = "Unknown"
    
    def authenticate(self) -> bool:
        """Authenticate with the email service."""
        raise NotImplementedError
    
    def get_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages from the email service."""
        raise NotImplementedError
    
    def send_message(self, to: str, subject: str, body: str) -> bool:
        """Send a message through the email service."""
        raise NotImplementedError
    
    def is_authenticated(self) -> bool:
        """Check if the service is authenticated."""
        return self.authenticated

class GmailProvider(EmailServiceProvider):
    """Gmail integration using Google API."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.service_name = "Gmail"
        self.client = None
        
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            if 'credentials' in config:
                creds = Credentials.from_authorized_user_info(config['credentials'])
                self.client = build('gmail', 'v1', credentials=creds)
                self.authenticated = True
        except ImportError:
            logger.warning("Google API client not available")
        except Exception as e:
            logger.warning("Gmail initialization failed: %s", e)
    
    def authenticate(self) -> bool:
        """Authenticate with Gmail."""
        if self.client:
            try:
                # Test the connection
                profile = self.client.users().getProfile(userId='me').execute()
                self.authenticated = True
                return True
            except Exception as e:
                logger.error("Gmail authentication failed: %s", e)
                return False
        return False
    
    def get_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent Gmail messages."""
        if not self.authenticated or not self.client:
            return []
        
        try:
            results = self.client.users().messages().list(
                userId='me', 
                maxResults=limit,
                q='is:unread'
            ).execute()
            
            messages = []
            for msg in results.get('messages', []):
                msg_detail = self.client.users().messages().get(
                    userId='me', 
                    id=msg['id']
                ).execute()
                
                headers = msg_detail['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                messages.append({
                    'id': msg['id'],
                    'subject': subject,
                    'sender': sender,
                    'date': date,
                    'snippet': msg_detail.get('snippet', ''),
                    'unread': 'UNREAD' in msg_detail.get('labelIds', [])
                })
            
            return messages
            
        except Exception as e:
            logger.error("Failed to get Gmail messages: %s", e)
            return []
    
    def send_message(self, to: str, subject: str, body: str) -> bool:
        """Send a message via Gmail."""
        if not self.authenticated or not self.client:
            return False
        
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            self.client.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error("Failed to send Gmail message: %s", e)
            return False

class OutlookProvider(EmailServiceProvider):
    """Microsoft Outlook integration using Graph API."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.service_name = "Outlook"
        self.access_token = config.get('access_token')
        self.client_id = config.get('client_id')
        self.client_secret = config.get('client_secret')
        self.tenant_id = config.get('tenant_id')
    
    def authenticate(self) -> bool:
        """Authenticate with Microsoft Graph API."""
        if not self.access_token:
            return False
        
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Test the connection
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me',
                headers=headers
            )
            
            if response.status_code == 200:
                self.authenticated = True
                return True
            else:
                logger.error("Outlook authentication failed: %s", response.status_code)
                return False
                
        except ImportError:
            logger.warning("Requests library not available for Outlook integration")
            return False
        except Exception as e:
            logger.error("Outlook authentication error: %s", e)
            return False
    
    def get_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent Outlook messages."""
        if not self.authenticated:
            return []
        
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f'https://graph.microsoft.com/v1.0/me/messages?$top={limit}&$orderby=receivedDateTime desc',
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                messages = []
                
                for msg in data.get('value', []):
                    messages.append({
                        'id': msg['id'],
                        'subject': msg.get('subject', 'No Subject'),
                        'sender': msg.get('from', {}).get('emailAddress', {}).get('address', 'Unknown'),
                        'date': msg.get('receivedDateTime', ''),
                        'snippet': msg.get('bodyPreview', ''),
                        'unread': not msg.get('isRead', False)
                    })
                
                return messages
            else:
                logger.error("Failed to get Outlook messages: %s", response.status_code)
                return []
                
        except Exception as e:
            logger.error("Outlook message retrieval error: %s", e)
            return []
    
    def send_message(self, to: str, subject: str, body: str) -> bool:
        """Send a message via Outlook."""
        if not self.authenticated:
            return False
        
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            message_data = {
                'message': {
                    'subject': subject,
                    'body': {
                        'contentType': 'Text',
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
            
            response = requests.post(
                'https://graph.microsoft.com/v1.0/me/sendMail',
                headers=headers,
                json=message_data
            )
            
            return response.status_code == 202
            
        except Exception as e:
            logger.error("Failed to send Outlook message: %s", e)
            return False

class IMAPProvider(EmailServiceProvider):
    """Generic IMAP/SMTP provider for Yahoo, AOL, and other services."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.service_name = config.get('service_name', 'IMAP')
        self.imap_server = config.get('imap_server')
        self.imap_port = config.get('imap_port', 993)
        self.smtp_server = config.get('smtp_server')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.use_ssl = config.get('use_ssl', True)
    
    def authenticate(self) -> bool:
        """Authenticate with IMAP server."""
        if not all([self.imap_server, self.username, self.password]):
            return False
        
        try:
            if self.use_ssl:
                self.imap_conn = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            else:
                self.imap_conn = imaplib.IMAP4(self.imap_server, self.imap_port)
            
            self.imap_conn.login(self.username, self.password)
            self.imap_conn.select('INBOX')
            self.authenticated = True
            return True
            
        except Exception as e:
            logger.error("IMAP authentication failed: %s", e)
            return False
    
    def get_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent IMAP messages."""
        if not self.authenticated:
            return []
        
        try:
            # Search for unread messages
            status, messages = self.imap_conn.search(None, 'UNSEEN')
            
            if status != 'OK':
                return []
            
            message_ids = messages[0].split()
            recent_ids = message_ids[-limit:] if len(message_ids) > limit else message_ids
            
            messages_data = []
            for msg_id in recent_ids:
                status, msg_data = self.imap_conn.fetch(msg_id, '(RFC822)')
                
                if status == 'OK':
                    import email
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    messages_data.append({
                        'id': msg_id.decode(),
                        'subject': msg.get('Subject', 'No Subject'),
                        'sender': msg.get('From', 'Unknown Sender'),
                        'date': msg.get('Date', ''),
                        'snippet': msg.get_payload()[:100] if msg.get_payload() else '',
                        'unread': True
                    })
            
            return messages_data
            
        except Exception as e:
            logger.error("Failed to get IMAP messages: %s", e)
            return []
    
    def send_message(self, to: str, subject: str, body: str) -> bool:
        """Send a message via SMTP."""
        if not self.authenticated or not all([self.smtp_server, self.username, self.password]):
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = to
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            logger.error("Failed to send IMAP message: %s", e)
            return False

class EmailServiceManager:
    """Manages multiple email service providers."""
    
    def __init__(self):
        self.providers: Dict[str, EmailServiceProvider] = {}
        self.active_provider: Optional[str] = None
    
    def add_provider(self, name: str, provider: EmailServiceProvider) -> bool:
        """Add an email service provider."""
        if provider.authenticate():
            self.providers[name] = provider
            if not self.active_provider:
                self.active_provider = name
            logger.info("%s provider added successfully", provider.service_name)
            return True
        else:
            logger.error("Failed to add %s provider", provider.service_name)
            return False
    
    def get_active_provider(self) -> Optional[EmailServiceProvider]:
        """Get the currently active email provider."""
        if self.active_provider and self.active_provider in self.providers:
            return self.providers[self.active_provider]
        return None
    
    def switch_provider(self, name: str) -> bool:
        """Switch to a different email provider."""
        if name in self.providers:
            self.active_provider = name
            logger.info("Switched to %s", self.providers[name].service_name)
            return True
        return False
    
    def get_all_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get messages from the active provider."""
        provider = self.get_active_provider()
        if provider:
            return provider.get_messages(limit)
        return []
    
    def send_message(self, to: str, subject: str, body: str) -> bool:
        """Send a message via the active provider."""
        provider = self.get_active_provider()
        if provider:
            return provider.send_message(to, subject, body)
        return False
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers."""
        status = {}
        for name, provider in self.providers.items():
            status[name] = {
                'service_name': provider.service_name,
                'authenticated': provider.authenticated,
                'active': name == self.active_provider
            }
        return status

# Pre-configured provider templates
PROVIDER_CONFIGS = {
    'gmail': {
        'service_name': 'Gmail',
        'imap_server': 'imap.gmail.com',
        'imap_port': 993,
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'use_ssl': True
    },
    'outlook': {
        'service_name': 'Outlook',
        'imap_server': 'outlook.office365.com',
        'imap_port': 993,
        'smtp_server': 'smtp.office365.com',
        'smtp_port': 587,
        'use_ssl': True
    },
    'yahoo': {
        'service_name': 'Yahoo Mail',
        'imap_server': 'imap.mail.yahoo.com',
        'imap_port': 993,
        'smtp_server': 'smtp.mail.yahoo.com',
        'smtp_port': 587,
        'use_ssl': True
    },
    'aol': {
        'service_name': 'AOL Mail',
        'imap_server': 'imap.aol.com',
        'imap_port': 993,
        'smtp_server': 'smtp.aol.com',
        'smtp_port': 587,
        'use_ssl': True
    }
}

def create_email_service_manager() -> EmailServiceManager:
    """Create and return an email service manager instance."""
    manager = EmailServiceManager()
    
    # Add Gmail provider if credentials are available
    gmail_creds = os.getenv('GMAIL_CREDENTIALS')
    if gmail_creds:
        try:
            gmail_config = json.loads(gmail_creds)
            gmail_provider = GmailProvider(gmail_config)
            manager.add_provider('gmail', gmail_provider)
        except Exception as e:
            logger.warning("Gmail provider setup failed: %s", e)
    
    # Add Microsoft Graph provider if credentials are available
    microsoft_client_id = os.getenv('MICROSOFT_CLIENT_ID')
    if microsoft_client_id:
        try:
            from integrations.outlook.outlook_client import MicrosoftGraphProvider
            microsoft_config = {
                'client_id': microsoft_client_id,
                'client_secret': os.getenv('MICROSOFT_CLIENT_SECRET'),
                'tenant_id': os.getenv('MICROSOFT_TENANT_ID'),
                'redirect_uri': os.getenv('MICROSOFT_REDIRECT_URI'),
                'stored_tokens': {}
            }
            microsoft_provider = MicrosoftGraphProvider(microsoft_config)
            manager.add_provider('microsoft365', microsoft_provider)
        except Exception as e:
            logger.warning("Microsoft Graph provider setup failed: %s", e)
    
    # Add Mailchimp provider if credentials are available
    mailchimp_api_key = os.getenv('MAILCHIMP_API_KEY')
    if mailchimp_api_key:
        try:
            from integrations.mailchimp.mailchimp_client import MailchimpProvider
            mailchimp_config = {
                'api_key': mailchimp_api_key,
                'server_prefix': os.getenv('MAILCHIMP_SERVER_PREFIX', 'us1'),
                'list_id': os.getenv('MAILCHIMP_LIST_ID'),
                'webhook_secret': os.getenv('MAILCHIMP_WEBHOOK_SECRET')
            }
            mailchimp_provider = MailchimpProvider(mailchimp_config)
            manager.add_provider('mailchimp', mailchimp_provider)
        except Exception as e:
            logger.warning("Mailchimp provider setup failed: %s", e)
    
    # Add Apple iCloud provider if credentials are available
    apple_team_id = os.getenv('APPLE_TEAM_ID')
    if apple_team_id:
        try:
            from integrations.apple_icloud.icloud_client import AppleiCloudProvider
            apple_config = {
                'team_id': apple_team_id,
                'key_id': os.getenv('APPLE_KEY_ID'),
                'private_key': os.getenv('APPLE_PRIVATE_KEY'),
                'bundle_id': os.getenv('APPLE_BUNDLE_ID')
            }
            apple_provider = AppleiCloudProvider(apple_config)
            manager.add_provider('icloud', apple_provider)
        except Exception as e:
            logger.warning("Apple iCloud provider setup failed: %s", e)
    
    # Add Outlook provider if credentials are available (legacy)
    outlook_token = os.getenv('OUTLOOK_ACCESS_TOKEN')
    if outlook_token:
        try:
            outlook_config = {
                'access_token': outlook_token,
                'client_id': os.getenv('OUTLOOK_CLIENT_ID'),
                'client_secret': os.getenv('OUTLOOK_CLIENT_SECRET'),
                'tenant_id': os.getenv('OUTLOOK_TENANT_ID')
            }
            outlook_provider = OutlookProvider(outlook_config)
            manager.add_provider('outlook', outlook_provider)
        except Exception as e:
            logger.warning("Outlook provider setup failed: %s", e)
    
    return manager

if __name__ == "__main__":
    logger.info("Testing Email Service Integration Framework...")
    manager = create_email_service_manager()
    status = manager.get_provider_status()
    for name, info in status.items():
        logger.info("  %s: %s - %s", name, info['service_name'], 'ok' if info['authenticated'] else 'not authenticated')
    if manager.active_provider:
        logger.info("Active Provider: %s", manager.active_provider)
        messages = manager.get_all_messages(5)
        logger.info("Recent Messages (%d)", len(messages))
        for msg in messages:
            logger.info("  %s from %s", msg['subject'], msg['sender'])
    else:
        logger.warning("No active email provider configured")
