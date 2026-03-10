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

# Import timeout utilities
try:
    from core.api_timeouts import gmail_execute_with_timeout, DEFAULT_GMAIL_TIMEOUT
    from core.circuit_breaker import get_circuit_breaker
    TIMEOUT_AVAILABLE = True
except ImportError:
    TIMEOUT_AVAILABLE = False
    logger.warning("Gmail timeout utilities not available")


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
            # Get message list with timeout protection
            def _execute():
                return self.service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=max_results
                ).execute()
            
            if TIMEOUT_AVAILABLE:
                breaker = get_circuit_breaker("gmail", failure_threshold=3, timeout_seconds=60, fail_open=True)
                results = breaker.call(lambda: gmail_execute_with_timeout(_execute, DEFAULT_GMAIL_TIMEOUT))
            else:
                results = _execute()
            
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
            def _execute():
                return self.service.users().messages().get(
                    userId='me',
                    id=message_id,
                    format='full'
                ).execute()
            
            if TIMEOUT_AVAILABLE:
                breaker = get_circuit_breaker("gmail", failure_threshold=3, timeout_seconds=60, fail_open=True)
                message = breaker.call(lambda: gmail_execute_with_timeout(_execute, DEFAULT_GMAIL_TIMEOUT))
            else:
                message = _execute()
            
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
            def _execute():
                return self.service.users().threads().get(
                    userId='me',
                    id=thread_id
                ).execute()
            
            if TIMEOUT_AVAILABLE:
                breaker = get_circuit_breaker("gmail", failure_threshold=3, timeout_seconds=60, fail_open=True)
                thread = breaker.call(lambda: gmail_execute_with_timeout(_execute, DEFAULT_GMAIL_TIMEOUT))
            else:
                thread = _execute()
            
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
            def _execute():
                return self.service.users().messages().modify(
                    userId='me',
                    id=message_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
            
            if TIMEOUT_AVAILABLE:
                breaker = get_circuit_breaker("gmail", failure_threshold=3, timeout_seconds=60, fail_open=True)
                breaker.call(lambda: gmail_execute_with_timeout(_execute, DEFAULT_GMAIL_TIMEOUT))
            else:
                _execute()
            
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
            def _execute():
                return self.service.users().messages().modify(
                    userId='me',
                    id=message_id,
                    body={'addLabelIds': label_ids}
                ).execute()
            
            if TIMEOUT_AVAILABLE:
                breaker = get_circuit_breaker("gmail", failure_threshold=3, timeout_seconds=60, fail_open=True)
                breaker.call(lambda: gmail_execute_with_timeout(_execute, DEFAULT_GMAIL_TIMEOUT))
            else:
                _execute()
            
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
            def _execute():
                return self.service.users().labels().list(userId='me').execute()
            
            if TIMEOUT_AVAILABLE:
                breaker = get_circuit_breaker("gmail", failure_threshold=3, timeout_seconds=60, fail_open=True)
                results = breaker.call(lambda: gmail_execute_with_timeout(_execute, DEFAULT_GMAIL_TIMEOUT))
            else:
                results = _execute()
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
            def _execute():
                return self.service.users().messages().list(
                    userId='me',
                    q="is:unread",
                    maxResults=1
                ).execute()
            
            if TIMEOUT_AVAILABLE:
                breaker = get_circuit_breaker("gmail", failure_threshold=3, timeout_seconds=60, fail_open=True)
                results = breaker.call(lambda: gmail_execute_with_timeout(_execute, DEFAULT_GMAIL_TIMEOUT))
            else:
                results = _execute()
            
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
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    logger.info("Testing Minimal Gmail Service")
    
    service = MinimalGmailService()
    
    # Test authentication
    logger.info("Testing authentication...")
    if service.authenticate():
        logger.info("Authentication successful")
        
        # Test getting labels
        logger.info("Testing labels...")
        labels = service.get_labels()
        if labels:
            logger.info("Found %s labels", len(labels))
            for label in labels[:3]:  # Show first 3
                logger.info("  - %s", label.get('name', 'Unknown'))
        
        # Test getting unread count
        logger.info("Testing unread count...")
        unread_count = service.get_unread_count()
        logger.info("Unread messages: %s", unread_count)
        
    else:
        logger.error("Authentication failed")
        logger.info("Make sure you have:")
        logger.info("1. Gmail API credentials in auth/credentials.json")
        logger.info("2. Run authentication first")
