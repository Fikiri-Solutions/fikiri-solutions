#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal Email Actions
Simple email management actions for the cleaned codebase.
"""

import logging
from typing import Optional

class EmailActions:
    """Minimal email management actions."""
    
    def __init__(self, service=None):
        """Initialize email actions."""
        self.service = service
        self.logger = logging.getLogger(__name__)
    
    def mark_as_read(self, msg_id: str) -> bool:
        """Mark message as read."""
        if not self.service:
            self.logger.error("Gmail service not initialized")
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except Exception as e:
            self.logger.error(f"Failed to mark as read: {e}")
            return False
    
    def mark_as_unread(self, msg_id: str) -> bool:
        """Mark message as unread."""
        if not self.service:
            self.logger.error("Gmail service not initialized")
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'addLabelIds': ['UNREAD']}
            ).execute()
            return True
        except Exception as e:
            self.logger.error(f"Failed to mark as unread: {e}")
            return False
    
    def archive_message(self, msg_id: str) -> bool:
        """Archive message."""
        if not self.service:
            self.logger.error("Gmail service not initialized")
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'removeLabelIds': ['INBOX']}
            ).execute()
            return True
        except Exception as e:
            self.logger.error(f"Failed to archive message: {e}")
            return False
    
    def delete_message(self, msg_id: str) -> bool:
        """Delete message."""
        if not self.service:
            self.logger.error("Gmail service not initialized")
            return False
        
        try:
            self.service.users().messages().delete(
                userId='me',
                id=msg_id
            ).execute()
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete message: {e}")
            return False
    
    def star_message(self, msg_id: str) -> bool:
        """Star message."""
        if not self.service:
            self.logger.error("Gmail service not initialized")
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'addLabelIds': ['STARRED']}
            ).execute()
            return True
        except Exception as e:
            self.logger.error(f"Failed to star message: {e}")
            return False
    
    def mark_as_important(self, msg_id: str) -> bool:
        """Mark message as important."""
        if not self.service:
            self.logger.error("Gmail service not initialized")
            return False
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'addLabelIds': ['IMPORTANT']}
            ).execute()
            return True
        except Exception as e:
            self.logger.error(f"Failed to mark as important: {e}")
            return False
