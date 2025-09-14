"""
Test Module for Fikiri Solutions - Gmail Lead Responder

This module provides comprehensive tests for all core functionality
including authentication, email parsing, Gmail operations, and actions.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import base64
from typing import Dict, Any, List

# Import modules to test
from core.auth import GmailAuthenticator, authenticate_gmail
from core.gmail_utils import GmailService, get_full_message, reply_to_email
from core.email_parser import EmailParser, get_sender, get_subject, get_body_text
from core.actions import EmailActions, archive_message, mark_as_read
from core.config import ConfigManager, FikiriConfig, GmailConfig, EmailConfig


class TestGmailAuthenticator(unittest.TestCase):
    """Test Gmail authentication functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.credentials_path = "test_credentials.json"
        self.token_path = "test_token.pkl"
        self.authenticator = GmailAuthenticator(self.credentials_path, self.token_path)
    
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('pickle.load')
    def test_load_existing_token(self, mock_pickle_load, mock_open, mock_exists):
        """Test loading existing token."""
        mock_exists.return_value = True
        mock_creds = Mock()
        mock_creds.valid = True
        mock_pickle_load.return_value = mock_creds
        
        creds = self.authenticator._load_token()
        self.assertEqual(creds, mock_creds)
    
    @patch('os.path.exists')
    def test_load_nonexistent_token(self, mock_exists):
        """Test loading non-existent token."""
        mock_exists.return_value = False
        creds = self.authenticator._load_token()
        self.assertIsNone(creds)
    
    def test_is_token_valid(self):
        """Test token validation."""
        mock_creds = Mock()
        mock_creds.valid = True
        self.assertTrue(self.authenticator._is_token_valid(mock_creds))
        
        mock_creds.valid = False
        self.assertFalse(self.authenticator._is_token_valid(mock_creds))
        
        self.assertFalse(self.authenticator._is_token_valid(None))


class TestEmailParser(unittest.TestCase):
    """Test email parsing functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = EmailParser()
        self.mock_message = self._create_mock_message()
    
    def _create_mock_message(self) -> Dict[str, Any]:
        """Create a mock Gmail message for testing."""
        return {
            "id": "test_msg_123",
            "threadId": "thread_456",
            "snippet": "This is a test email snippet",
            "payload": {
                "headers": [
                    {"name": "From", "value": "test@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"}
                ],
                "mimeType": "text/plain",
                "body": {
                    "data": base64.urlsafe_b64encode(b"Hello, this is a test email body.").decode()
                }
            },
            "labelIds": ["INBOX", "UNREAD"],
            "sizeEstimate": 1024,
            "historyId": "12345"
        }
    
    def test_parse_message(self):
        """Test complete message parsing."""
        parsed = self.parser.parse_message(self.mock_message)
        
        self.assertEqual(parsed["message_id"], "test_msg_123")
        self.assertEqual(parsed["thread_id"], "thread_456")
        self.assertEqual(parsed["snippet"], "This is a test email snippet")
        self.assertIn("from", parsed["headers"])
        self.assertEqual(parsed["headers"]["from"], "test@example.com")
        self.assertIn("text", parsed["body"])
        self.assertEqual(parsed["body"]["text"], "Hello, this is a test email body.")
    
    def test_parse_headers(self):
        """Test header parsing."""
        headers = [
            {"name": "From", "value": "sender@example.com"},
            {"name": "Subject", "value": "Test Subject"}
        ]
        
        parsed_headers = self.parser._parse_headers(headers)
        self.assertEqual(parsed_headers["from"], "sender@example.com")
        self.assertEqual(parsed_headers["subject"], "Test Subject")
    
    def test_parse_text_plain(self):
        """Test plain text body parsing."""
        payload = {
            "mimeType": "text/plain",
            "body": {
                "data": base64.urlsafe_b64encode(b"Plain text content").decode()
            }
        }
        
        result = self.parser._parse_text_plain(payload)
        self.assertEqual(result["text"], "Plain text content")
        self.assertEqual(result["html"], "")
    
    def test_get_header_value(self):
        """Test header value extraction."""
        headers = [
            {"name": "From", "value": "test@example.com"},
            {"name": "Subject", "value": "Test Subject"}
        ]
        
        from core.email_parser import get_header_value
        
        self.assertEqual(get_header_value(headers, "From"), "test@example.com")
        self.assertEqual(get_header_value(headers, "from"), "test@example.com")  # Case insensitive
        self.assertEqual(get_header_value(headers, "Subject"), "Test Subject")
        self.assertIsNone(get_header_value(headers, "NonExistent"))


class TestGmailService(unittest.TestCase):
    """Test Gmail service functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        self.gmail_service = GmailService(self.mock_service)
    
    def test_get_message(self):
        """Test message retrieval."""
        mock_message = {"id": "test_123", "threadId": "thread_456"}
        self.mock_service.users().messages().get().execute.return_value = mock_message
        
        result = self.gmail_service.get_message("test_123")
        self.assertEqual(result, mock_message)
    
    def test_list_messages(self):
        """Test message listing."""
        mock_response = {
            "messages": [
                {"id": "msg_1", "threadId": "thread_1"},
                {"id": "msg_2", "threadId": "thread_2"}
            ]
        }
        self.mock_service.users().messages().list().execute.return_value = mock_response
        
        result = self.gmail_service.list_messages("is:unread", 5)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "msg_1")
    
    def test_send_reply(self):
        """Test sending replies."""
        mock_original = {
            "threadId": "thread_123",
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Subject", "value": "Original Subject"}
                ]
            }
        }
        
        mock_sent = {"id": "reply_123"}
        
        self.mock_service.users().messages().get().execute.return_value = mock_original
        self.mock_service.users().messages().send().execute.return_value = mock_sent
        
        result = self.gmail_service.send_reply("msg_123", "Test reply")
        self.assertEqual(result, mock_sent)


class TestEmailActions(unittest.TestCase):
    """Test email actions functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_service = Mock()
        self.actions = EmailActions(self.mock_service)
    
    def test_mark_as_read(self):
        """Test marking message as read."""
        self.mock_service.users().messages().modify().execute.return_value = {}
        
        result = self.actions.mark_as_read("msg_123")
        self.assertTrue(result)
    
    def test_archive_message(self):
        """Test archiving message."""
        self.mock_service.users().messages().modify().execute.return_value = {}
        
        result = self.actions.archive_message("msg_123")
        self.assertTrue(result)
    
    def test_delete_message(self):
        """Test deleting message."""
        self.mock_service.users().messages().delete().execute.return_value = {}
        
        result = self.actions.delete_message("msg_123")
        self.assertTrue(result)
    
    def test_add_labels(self):
        """Test adding labels."""
        self.mock_service.users().messages().modify().execute.return_value = {}
        
        result = self.actions.add_labels("msg_123", ["LABEL_1", "LABEL_2"])
        self.assertTrue(result)
    
    def test_batch_archive(self):
        """Test batch archiving."""
        self.mock_service.users().messages().modify().execute.return_value = {}
        
        msg_ids = ["msg_1", "msg_2", "msg_3"]
        results = self.actions.batch_archive(msg_ids)
        
        self.assertEqual(len(results), 3)
        self.assertTrue(all(results.values()))


class TestConfigManager(unittest.TestCase):
    """Test configuration management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config_manager = ConfigManager("test_config.json")
    
    def test_create_default_config(self):
        """Test default configuration creation."""
        config = self.config_manager._create_default_config()
        
        self.assertIsInstance(config, FikiriConfig)
        self.assertIsInstance(config.gmail, GmailConfig)
        self.assertIsInstance(config.email, EmailConfig)
        self.assertEqual(config.gmail.user_id, 'me')
        self.assertFalse(config.debug)
        self.assertFalse(config.dry_run)
    
    def test_get_env_bool(self):
        """Test environment boolean parsing."""
        with patch.dict('os.environ', {'TEST_BOOL': 'true'}):
            result = self.config_manager._get_env_bool('TEST_BOOL', False)
            self.assertTrue(result)
        
        with patch.dict('os.environ', {'TEST_BOOL': 'false'}):
            result = self.config_manager._get_env_bool('TEST_BOOL', True)
            self.assertFalse(result)
        
        with patch.dict('os.environ', {}, clear=True):
            result = self.config_manager._get_env_bool('TEST_BOOL', True)
            self.assertTrue(result)


class TestMockData(unittest.TestCase):
    """Test with mock Gmail data."""
    
    def test_mock_email_processing(self):
        """Test complete email processing with mock data."""
        # Mock Gmail message
        mock_message = {
            "id": "mock_msg_123",
            "threadId": "mock_thread_456",
            "snippet": "Mock email snippet",
            "payload": {
                "headers": [
                    {"name": "From", "value": "lead@customer.com"},
                    {"name": "Subject", "value": "Service Request - Lawn Care"},
                    {"name": "To", "value": "business@fikiri.com"}
                ],
                "mimeType": "text/plain",
                "body": {
                    "data": base64.urlsafe_b64encode(
                        b"Hi, I need lawn care services for my property. Please contact me at 555-1234."
                    ).decode()
                }
            },
            "labelIds": ["INBOX", "UNREAD"],
            "sizeEstimate": 256
        }
        
        # Parse the mock message
        parser = EmailParser()
        parsed = parser.parse_message(mock_message)
        
        # Verify parsing results
        self.assertEqual(parsed["message_id"], "mock_msg_123")
        self.assertEqual(parsed["headers"]["from"], "lead@customer.com")
        self.assertEqual(parsed["headers"]["subject"], "Service Request - Lawn Care")
        self.assertIn("lawn care services", parsed["body"]["text"].lower())
        
        # Test lead classification (mock)
        email_type = self._classify_email_type(parsed)
        self.assertEqual(email_type, "lead")
    
    def _classify_email_type(self, parsed_data: Dict[str, Any]) -> str:
        """Mock email classification function."""
        subject = parsed_data.get("headers", {}).get("subject", "").lower()
        body = parsed_data.get("body", {}).get("text", "").lower()
        
        if any(keyword in subject + body for keyword in ["service", "quote", "price", "estimate"]):
            return "lead"
        elif any(keyword in subject + body for keyword in ["help", "support", "problem", "issue"]):
            return "support"
        elif any(keyword in subject + body for keyword in ["urgent", "asap", "emergency"]):
            return "urgent"
        else:
            return "general"


def create_mock_gmail_message(
    msg_id: str = "test_123",
    sender: str = "test@example.com",
    subject: str = "Test Subject",
    body: str = "Test email body",
    is_unread: bool = True
) -> Dict[str, Any]:
    """Create a mock Gmail message for testing."""
    labels = ["INBOX"]
    if is_unread:
        labels.append("UNREAD")
    
    return {
        "id": msg_id,
        "threadId": f"thread_{msg_id}",
        "snippet": body[:100] + "..." if len(body) > 100 else body,
        "payload": {
            "headers": [
                {"name": "From", "value": sender},
                {"name": "Subject", "value": subject},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"}
            ],
            "mimeType": "text/plain",
            "body": {
                "data": base64.urlsafe_b64encode(body.encode()).decode()
            }
        },
        "labelIds": labels,
        "sizeEstimate": len(body),
        "historyId": "12345"
    }


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
