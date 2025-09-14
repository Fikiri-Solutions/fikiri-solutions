#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal Email Parser
Simple email parsing for the cleaned codebase.
"""

import json
import base64
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class ParsedEmail:
    """Parsed email data structure."""
    headers: Dict[str, str]
    body: Dict[str, str]
    attachments: List[Dict[str, Any]]
    snippet: str
    message_id: str

class EmailParser:
    """Minimal email parser for Gmail messages."""
    
    def __init__(self):
        """Initialize the email parser."""
        self.supported_mime_types = [
            "text/plain",
            "text/html",
            "multipart/alternative",
            "multipart/mixed",
            "multipart/related"
        ]
    
    def parse_message(self, message: Dict[str, Any]) -> ParsedEmail:
        """
        Parse a Gmail message into structured data.
        
        Args:
            message: Gmail API message object
            
        Returns:
            ParsedEmail object with structured data
        """
        try:
            # Extract headers
            headers = {}
            if 'payload' in message and 'headers' in message['payload']:
                for header in message['payload']['headers']:
                    headers[header['name'].lower()] = header['value']
            
            # Extract body
            body = self._extract_body(message.get('payload', {}))
            
            # Extract snippet
            snippet = message.get('snippet', '')
            
            # Extract message ID
            message_id = message.get('id', '')
            
            # Extract attachments (simplified)
            attachments = self._extract_attachments(message.get('payload', {}))
            
            return ParsedEmail(
                headers=headers,
                body=body,
                attachments=attachments,
                snippet=snippet,
                message_id=message_id
            )
            
        except Exception as e:
            # Return minimal structure on error
            return ParsedEmail(
                headers={'from': 'unknown', 'subject': 'unknown'},
                body={'text': '', 'html': ''},
                attachments=[],
                snippet='',
                message_id=''
            )
    
    def _extract_body(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Extract text and HTML body from message payload."""
        body = {'text': '', 'html': ''}
        
        try:
            if 'body' in payload:
                # Single part message
                if 'data' in payload['body']:
                    content = self._decode_content(payload['body']['data'])
                    mime_type = payload.get('mimeType', 'text/plain')
                    
                    if 'text/html' in mime_type:
                        body['html'] = content
                    else:
                        body['text'] = content
            
            elif 'parts' in payload:
                # Multipart message
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain' and 'body' in part:
                        if 'data' in part['body']:
                            body['text'] = self._decode_content(part['body']['data'])
                    elif part.get('mimeType') == 'text/html' and 'body' in part:
                        if 'data' in part['body']:
                            body['html'] = self._decode_content(part['body']['data'])
            
        except Exception as e:
            body['text'] = f"Error parsing body: {e}"
        
        return body
    
    def _extract_attachments(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attachment information from message payload."""
        attachments = []
        
        try:
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('filename'):
                        attachment = {
                            'filename': part['filename'],
                            'mime_type': part.get('mimeType', 'application/octet-stream'),
                            'size': part.get('body', {}).get('size', 0),
                            'attachment_id': part.get('body', {}).get('attachmentId', '')
                        }
                        attachments.append(attachment)
        except Exception as e:
            pass  # Ignore attachment parsing errors
        
        return attachments
    
    def _decode_content(self, data: str) -> str:
        """Decode base64url encoded content."""
        try:
            # Add padding if needed
            missing_padding = len(data) % 4
            if missing_padding:
                data += '=' * (4 - missing_padding)
            
            # Decode base64url
            decoded_bytes = base64.urlsafe_b64decode(data)
            return decoded_bytes.decode('utf-8', errors='ignore')
        except Exception:
            return data  # Return original if decoding fails
