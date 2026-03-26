#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal Email Parser
Lightweight email parsing without heavy dependencies.
"""

import base64
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _safe_headers(pm: Any) -> Dict[str, Any]:
    if not isinstance(pm, dict):
        return {}
    h = pm.get("headers")
    return h if isinstance(h, dict) else {}


def _safe_body(pm: Any) -> Dict[str, Any]:
    if not isinstance(pm, dict):
        return {"text": "", "html": ""}
    b = pm.get("body")
    return b if isinstance(b, dict) else {"text": "", "html": ""}


def _safe_labels(pm: Any) -> List[Any]:
    if not isinstance(pm, dict):
        return []
    raw = pm.get("labels")
    return raw if isinstance(raw, list) else []


def _safe_attachments(pm: Any) -> List[Any]:
    if not isinstance(pm, dict):
        return []
    raw = pm.get("attachments")
    return raw if isinstance(raw, list) else []


def _payload_body_block(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    b = payload.get("body")
    return b if isinstance(b, dict) else {}


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
            _lid = message.get("labelIds", [])
            parsed["labels"] = _lid if isinstance(_lid, list) else []
            
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
        if not isinstance(payload, dict):
            return
        mime_type = payload.get('mimeType', '')
        body_block = _payload_body_block(payload)

        if mime_type == 'text/plain':
            body_data = body_block.get('data', '')
            if body_data:
                parsed["body"]["text"] = self._decode_base64(body_data)

        elif mime_type == 'text/html':
            body_data = body_block.get('data', '')
            if body_data:
                parsed["body"]["html"] = self._decode_base64(body_data)

        elif mime_type.startswith('multipart/'):
            parts = payload.get('parts', [])
            if not isinstance(parts, list):
                parts = []
            for part in parts:
                self._extract_body_and_attachments(part, parsed)

        # Check for attachments
        if 'filename' in payload and payload['filename']:
            attachment = {
                "filename": payload['filename'],
                "mime_type": payload.get('mimeType', ''),
                "size": body_block.get('size', 0),
                "attachment_id": body_block.get('attachmentId', '')
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
        return _safe_headers(parsed_message).get("from", "")

    def get_subject(self, parsed_message: Dict[str, Any]) -> str:
        """Extract subject from parsed message."""
        return _safe_headers(parsed_message).get("subject", "")

    def get_recipients(self, parsed_message: Dict[str, Any]) -> List[str]:
        """Extract recipient emails from parsed message."""
        hdr = _safe_headers(parsed_message)
        to = hdr.get("to", "")
        cc = hdr.get("cc", "")
        bcc = hdr.get("bcc", "")
        
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
        body = _safe_body(parsed_message)
        text_body = body.get("text", "")
        html_body = body.get("html", "")
        
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
        return "UNREAD" in _safe_labels(parsed_message)

    def is_important(self, parsed_message: Dict[str, Any]) -> bool:
        """Check if message is marked as important."""
        return "IMPORTANT" in _safe_labels(parsed_message)

    def has_attachments(self, parsed_message: Dict[str, Any]) -> bool:
        """Check if message has attachments."""
        return len(_safe_attachments(parsed_message)) > 0

    def get_attachment_count(self, parsed_message: Dict[str, Any]) -> int:
        """Get number of attachments."""
        return len(_safe_attachments(parsed_message))

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

