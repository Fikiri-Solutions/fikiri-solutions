#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal Email Parser
Lightweight email parsing without heavy dependencies.
"""

import json
import base64
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class MinimalEmailParser:
    """Minimal email parser - lightweight version."""
    
    def __init__(self):
        """Initialize the minimal email parser."""
        self.supported_mime_types = [
            "text/plain",
            "text/html",
            "multipart/alternative",
            "multipart/mixed",
            "multipart/related"
        ]
    
    def parse_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a Gmail message into structured data.
        
        Args:
            message: Gmail API message object
            
        Returns:
            Dictionary with parsed email data
        """
        try:
            parsed = {
                "headers": {},
                "body": {"text": "", "html": ""},
                "attachments": [],
                "snippet": "",
                "message_id": "",
                "thread_id": "",
                "labels": []
            }
            
            # Extract basic message info
            parsed["message_id"] = message.get("id", "")
            parsed["thread_id"] = message.get("threadId", "")
            parsed["snippet"] = message.get("snippet", "")
            parsed["labels"] = message.get("labelIds", [])
            
            # Extract headers
            if 'payload' in message and 'headers' in message['payload']:
                for header in message['payload']['headers']:
                    name = header.get('name', '').lower()
                    value = header.get('value', '')
                    parsed["headers"][name] = value
            
            # Extract body and attachments
            self._extract_body_and_attachments(message.get('payload', {}), parsed)
            
            return parsed
            
        except Exception as e:
            logger.error("Error parsing message: %s", e)
            return self._create_empty_parsed_message()
    
    def _extract_body_and_attachments(self, payload: Dict[str, Any], parsed: Dict[str, Any]):
        """Extract body text and attachments from payload."""
        mime_type = payload.get('mimeType', '')
        
        if mime_type == 'text/plain':
            body_data = payload.get('body', {}).get('data', '')
            if body_data:
                parsed["body"]["text"] = self._decode_base64(body_data)
        
        elif mime_type == 'text/html':
            body_data = payload.get('body', {}).get('data', '')
            if body_data:
                parsed["body"]["html"] = self._decode_base64(body_data)
        
        elif mime_type.startswith('multipart/'):
            parts = payload.get('parts', [])
            for part in parts:
                self._extract_body_and_attachments(part, parsed)
        
        # Check for attachments
        if 'filename' in payload and payload['filename']:
            attachment = {
                "filename": payload['filename'],
                "mime_type": payload.get('mimeType', ''),
                "size": payload.get('body', {}).get('size', 0),
                "attachment_id": payload.get('body', {}).get('attachmentId', '')
            }
            parsed["attachments"].append(attachment)
    
    def _decode_base64(self, data: str) -> str:
        """Decode base64 data."""
        try:
            # Add padding if needed
            missing_padding = len(data) % 4
            if missing_padding:
                data += '=' * (4 - missing_padding)
            
            decoded_bytes = base64.urlsafe_b64decode(data)
            return decoded_bytes.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.error("Error decoding base64: %s", e)
            return ""
    
    def _create_empty_parsed_message(self) -> Dict[str, Any]:
        """Create an empty parsed message structure."""
        return {
            "headers": {},
            "body": {"text": "", "html": ""},
            "attachments": [],
            "snippet": "",
            "message_id": "",
            "thread_id": "",
            "labels": []
        }
    
    def get_sender(self, parsed_message: Dict[str, Any]) -> str:
        """Extract sender email from parsed message."""
        return parsed_message.get("headers", {}).get("from", "")
    
    def get_subject(self, parsed_message: Dict[str, Any]) -> str:
        """Extract subject from parsed message."""
        return parsed_message.get("headers", {}).get("subject", "")
    
    def get_recipients(self, parsed_message: Dict[str, Any]) -> List[str]:
        """Extract recipient emails from parsed message."""
        to = parsed_message.get("headers", {}).get("to", "")
        cc = parsed_message.get("headers", {}).get("cc", "")
        bcc = parsed_message.get("headers", {}).get("bcc", "")
        
        recipients = []
        if to:
            recipients.extend(self._parse_email_list(to))
        if cc:
            recipients.extend(self._parse_email_list(cc))
        if bcc:
            recipients.extend(self._parse_email_list(bcc))
        
        return recipients
    
    def _parse_email_list(self, email_string: str) -> List[str]:
        """Parse comma-separated email list."""
        if not email_string:
            return []
        
        emails = []
        for email in email_string.split(','):
            email = email.strip()
            if email:
                emails.append(email)
        
        return emails
    
    def get_body_text(self, parsed_message: Dict[str, Any]) -> str:
        """Get the text body of the email."""
        text_body = parsed_message.get("body", {}).get("text", "")
        html_body = parsed_message.get("body", {}).get("html", "")
        
        # Prefer text, fallback to HTML
        if text_body:
            return text_body
        elif html_body:
            # Simple HTML tag removal (basic)
            import re
            clean_text = re.sub(r'<[^>]+>', '', html_body)
            return clean_text.strip()
        
        return ""
    
    def is_unread(self, parsed_message: Dict[str, Any]) -> bool:
        """Check if message is unread."""
        labels = parsed_message.get("labels", [])
        return "UNREAD" in labels
    
    def is_important(self, parsed_message: Dict[str, Any]) -> bool:
        """Check if message is marked as important."""
        labels = parsed_message.get("labels", [])
        return "IMPORTANT" in labels
    
    def has_attachments(self, parsed_message: Dict[str, Any]) -> bool:
        """Check if message has attachments."""
        attachments = parsed_message.get("attachments", [])
        return len(attachments) > 0
    
    def get_attachment_count(self, parsed_message: Dict[str, Any]) -> int:
        """Get number of attachments."""
        attachments = parsed_message.get("attachments", [])
        return len(attachments)

def parse_email_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Simple function to parse an email message."""
    parser = MinimalEmailParser()
    return parser.parse_message(message)

if __name__ == "__main__":
    # Test with a sample message structure
    sample_message = {
        "id": "test123",
        "threadId": "thread123",
        "snippet": "This is a test email",
        "labelIds": ["UNREAD"],
        "payload": {
            "headers": [
                {"name": "From", "value": "test@example.com"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Subject", "value": "Test Subject"}
            ],
            "mimeType": "text/plain",
            "body": {
                "data": base64.urlsafe_b64encode(b"Hello, this is a test email body.").decode('utf-8').rstrip('=')
            }
        }
    }
    
    parser = MinimalEmailParser()
    parsed = parser.parse_message(sample_message)
    
    logger.info("Testing Minimal Email Parser")
    logger.info("Message ID: %s", parsed['message_id'])
    logger.info("Sender: %s", parser.get_sender(parsed))
    logger.info("Subject: %s", parser.get_subject(parsed))
    logger.info("Body: %s", parser.get_body_text(parsed))
    logger.info("Is Unread: %s", parser.is_unread(parsed))
    logger.info("Has Attachments: %s", parser.has_attachments(parsed))

