#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal Gmail Utils
Lightweight Gmail API operations without heavy dependencies.
"""

import json
import logging
import pickle
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class MinimalGmailService:
    """Minimal Gmail service - lightweight version."""
    
    def __init__(self, credentials_path: str = "auth/credentials.json", token_path: str = "auth/token.pkl"):
        """Initialize minimal Gmail service."""
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.authenticated = False
    
    def authenticate(self) -> bool:
        """Authenticate with Gmail API."""
        try:
            # Import Google API libraries only when needed
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            
            creds = None
            
            # Load existing token
            if Path(self.token_path).exists():
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            # If no valid credentials, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, 
                        ['https://www.googleapis.com/auth/gmail.readonly']
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save credentials
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
            
            # Build service
            self.service = build('gmail', 'v1', credentials=creds)
            self.authenticated = True
            logger.info("Gmail service authenticated")
            return True
            
        except Exception as e:
            logger.error("Gmail authentication failed: %s", e)
            self.authenticated = False
            return False
    
    def is_authenticated(self) -> bool:
        """Check if service is authenticated."""
        return self.authenticated and self.service is not None
    
    def get_messages(self, query: str = "is:unread", max_results: int = 10) -> List[Dict[str, Any]]:
        """Get messages from Gmail."""
        if not self.is_authenticated():
            logger.warning("Not authenticated. Run authenticate() first.")
            return []
        
        try:
            # Get message list
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            logger.info("Found %s messages", len(messages))
            return messages
            
        except Exception as e:
            logger.error("Error getting messages: %s", e)
            return []
    
    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific message by ID."""
        if not self.is_authenticated():
            logger.warning("Not authenticated. Run authenticate() first.")
            return None
        
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            logger.info("Retrieved message: %s", message_id)
            return message
        except Exception as e:
            logger.error("Error getting message %s: %s", message_id, e)
            return None
    
    def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get a thread by ID."""
        if not self.is_authenticated():
            logger.warning("Not authenticated. Run authenticate() first.")
            return None
        
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id
            ).execute()
            logger.info("Retrieved thread: %s", thread_id)
            return thread
        except Exception as e:
            logger.error("Error getting thread %s: %s", thread_id, e)
            return None
    
    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read."""
        if not self.is_authenticated():
            logger.warning("Not authenticated. Run authenticate() first.")
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            logger.info("Marked message %s as read", message_id)
            return True
        except Exception as e:
            logger.error("Error marking message as read: %s", e)
            return False
    
    def add_label(self, message_id: str, label_ids: List[str]) -> bool:
        """Add labels to a message."""
        if not self.is_authenticated():
            logger.warning("Not authenticated. Run authenticate() first.")
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': label_ids}
            ).execute()
            logger.info("Added labels to message %s", message_id)
            return True
        except Exception as e:
            logger.error("Error adding labels: %s", e)
            return False
    
    def get_labels(self) -> List[Dict[str, Any]]:
        """Get all Gmail labels."""
        if not self.is_authenticated():
            logger.warning("Not authenticated. Run authenticate() first.")
            return []
        
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            logger.info("Retrieved %s labels", len(labels))
            return labels
        except Exception as e:
            logger.error("Error getting labels: %s", e)
            return []
    
    def search_messages(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for messages with a query."""
        return self.get_messages(query, max_results)
    
    def get_unread_count(self) -> int:
        """Get count of unread messages."""
        messages = self.get_messages("is:unread", max_results=1)
        if not messages:
            return 0
        
        # Get total count
        try:
            results = self.service.users().messages().list(
                userId='me',
                q="is:unread",
                maxResults=1
            ).execute()
            
            total_count = results.get('resultSizeEstimate', 0)
            logger.info("Unread messages: %s", total_count)
            return total_count
        except Exception as e:
            logger.error("Error getting unread count: %s", e)
            return 0

def create_gmail_service(credentials_path: str = "auth/credentials.json", token_path: str = "auth/token.pkl") -> MinimalGmailService:
    """Create and return a Gmail service instance."""
    service = MinimalGmailService(credentials_path, token_path)
    return service

if __name__ == "__main__":
    # Test the Gmail service
    print("🧪 Testing Minimal Gmail Service")
    print("=" * 40)
    
    service = MinimalGmailService()
    
    # Test authentication
    print("Testing authentication...")
    if service.authenticate():
        print("✅ Authentication successful")
        
        # Test getting labels
        print("\nTesting labels...")
        labels = service.get_labels()
        if labels:
            print(f"✅ Found {len(labels)} labels")
            for label in labels[:3]:  # Show first 3
                print(f"   - {label.get('name', 'Unknown')}")
        
        # Test getting unread count
        print("\nTesting unread count...")
        unread_count = service.get_unread_count()
        print(f"✅ Unread messages: {unread_count}")
        
    else:
        print("❌ Authentication failed")
        print("📝 Make sure you have:")
        print("1. Gmail API credentials in auth/credentials.json")
        print("2. Run authentication first")
