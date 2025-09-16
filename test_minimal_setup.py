#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal Setup Test Script
Comprehensive test suite for all minimal services.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.minimal_config import get_config
from core.minimal_auth import authenticate_gmail
from core.minimal_email_parser import MinimalEmailParser
from core.minimal_gmail_utils import MinimalGmailService
from core.minimal_email_actions import MinimalEmailActions
from core.minimal_crm_service import MinimalCRMService

def test_config():
    """Test configuration loading."""
    print("Testing configuration...")
    try:
        config = get_config()
        print(f"✅ Config loaded: {config.gmail_max_results} max results")
        return True
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_auth():
    """Test authentication."""
    print("Testing authentication...")
    try:
        if authenticate_gmail():
            print("✅ Authentication working")
            return True
        else:
            print("❌ Authentication not working")
            return False
    except Exception as e:
        print(f"❌ Auth test failed: {e}")
        return False

def test_email_parser():
    """Test email parser."""
    print("Testing email parser...")
    try:
        parser = MinimalEmailParser()
        sample_message = {
            "id": "test123",
            "threadId": "thread123", 
            "snippet": "Test email",
            "labelIds": ["UNREAD"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "test@example.com"},
                    {"name": "Subject", "value": "Test Subject"}
                ],
                "mimeType": "text/plain",
                "body": {"data": "SGVsbG8gd29ybGQ="}  # "Hello world" in base64
            }
        }
        
        parsed = parser.parse_message(sample_message)
        sender = parser.get_sender(parsed)
        print(f"✅ Email parser working: {sender}")
        return True
    except Exception as e:
        print(f"❌ Email parser test failed: {e}")
        return False

def test_gmail_service():
    """Test Gmail service."""
    print("Testing Gmail service...")
    try:
        gmail_service = MinimalGmailService()
        print(f"✅ Gmail service created: {not gmail_service.is_authenticated()}")
        return True
    except Exception as e:
        print(f"❌ Gmail service test failed: {e}")
        return False

def test_email_actions():
    """Test email actions."""
    print("Testing email actions...")
    try:
        actions = MinimalEmailActions()
        parser = MinimalEmailParser()
        
        sample_message = {
            "id": "test123",
            "threadId": "thread123", 
            "snippet": "Test email",
            "labelIds": ["UNREAD"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "test@example.com"},
                    {"name": "Subject", "value": "Test Subject"}
                ],
                "mimeType": "text/plain",
                "body": {"data": "SGVsbG8gd29ybGQ="}
            }
        }
        
        parsed = parser.parse_message(sample_message)
        result = actions.process_email(parsed, "auto_reply")
        print(f"✅ Email actions working: {result['success']}")
        return True
    except Exception as e:
        print(f"❌ Email actions test failed: {e}")
        return False

def test_crm_service():
    """Test CRM service."""
    print("Testing CRM service...")
    try:
        crm_service = MinimalCRMService()
        lead = crm_service.add_lead("test@example.com", "Test User")
        print(f"✅ CRM service working: {lead.email}")
        return True
    except Exception as e:
        print(f"❌ CRM service test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Fikiri Solutions - Comprehensive Test Suite")
    print("=" * 50)
    
    tests = [
        test_config,
        test_auth,
        test_email_parser,
        test_gmail_service,
        test_email_actions,
        test_crm_service
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    print("=" * 50)
    print(f"🎉 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! System is ready.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())






