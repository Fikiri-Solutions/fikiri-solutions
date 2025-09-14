#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal Setup Test
Test script to verify the minimal setup works correctly.
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all minimal modules can be imported."""
    print("🧪 Testing Module Imports...")
    
    try:
        from core.minimal_config import get_config, MinimalConfig
        print("✅ minimal_config imported")
    except ImportError as e:
        print(f"❌ minimal_config import failed: {e}")
        return False
    
    try:
        from core.minimal_auth import MinimalAuthenticator, setup_auth
        print("✅ minimal_auth imported")
    except ImportError as e:
        print(f"❌ minimal_auth import failed: {e}")
        return False
    
    try:
        from core.minimal_email_parser import MinimalEmailParser, parse_email_message
        print("✅ minimal_email_parser imported")
    except ImportError as e:
        print(f"❌ minimal_email_parser import failed: {e}")
        return False
    
    try:
        from core.minimal_gmail_utils import MinimalGmailService
        print("✅ minimal_gmail_utils imported")
    except ImportError as e:
        print(f"❌ minimal_gmail_utils import failed: {e}")
        return False
    
    try:
        from core.minimal_email_actions import MinimalEmailActions
        print("✅ minimal_email_actions imported")
    except ImportError as e:
        print(f"❌ minimal_email_actions import failed: {e}")
        return False
    
    try:
        from core.minimal_crm_service import MinimalCRMService
        print("✅ minimal_crm_service imported")
    except ImportError as e:
        print(f"❌ minimal_crm_service import failed: {e}")
        return False
    
    return True

def test_config():
    """Test configuration functionality."""
    print("\n⚙️  Testing Configuration...")
    
    try:
        from core.minimal_config import get_config
        config = get_config()
        
        # Test basic properties
        assert hasattr(config, 'gmail_max_results')
        assert hasattr(config, 'is_debug')
        assert hasattr(config, 'is_dry_run')
        
        print(f"✅ Config loaded: {config.gmail_max_results} max results")
        print(f"✅ Debug mode: {config.is_debug()}")
        print(f"✅ Dry run: {config.is_dry_run()}")
        
        return True
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_auth():
    """Test authentication functionality."""
    print("\n🔐 Testing Authentication...")
    
    try:
        from core.minimal_auth import MinimalAuthenticator
        
        auth = MinimalAuthenticator()
        
        # Test credential file check
        creds_exist = auth.check_credentials_file()
        print(f"✅ Credentials check: {'Found' if creds_exist else 'Not found'}")
        
        # Test token file check
        token_exist = auth.check_token_file()
        print(f"✅ Token check: {'Found' if token_exist else 'Not found'}")
        
        # Test authentication status
        is_auth = auth.is_authenticated()
        print(f"✅ Authentication: {'Valid' if is_auth else 'Invalid'}")
        
        return True
    except Exception as e:
        print(f"❌ Auth test failed: {e}")
        return False

def test_email_parser():
    """Test email parser functionality."""
    print("\n📧 Testing Email Parser...")
    
    try:
        from core.minimal_email_parser import MinimalEmailParser
        import base64
        
        parser = MinimalEmailParser()
        
        # Create test message
        test_message = {
            "id": "test123",
            "threadId": "thread123",
            "snippet": "Test email snippet",
            "labelIds": ["UNREAD", "INBOX"],
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"}
                ],
                "mimeType": "text/plain",
                "body": {
                    "data": base64.urlsafe_b64encode(b"Hello, this is a test email body.").decode('utf-8').rstrip('=')
                }
            }
        }
        
        # Parse message
        parsed = parser.parse_message(test_message)
        
        # Test parsing results
        assert parsed["message_id"] == "test123"
        assert parser.get_sender(parsed) == "sender@example.com"
        assert parser.get_subject(parsed) == "Test Subject"
        assert parser.is_unread(parsed) == True
        assert parser.has_attachments(parsed) == False
        
        print(f"✅ Message parsed: {parsed['message_id']}")
        print(f"✅ Sender: {parser.get_sender(parsed)}")
        print(f"✅ Subject: {parser.get_subject(parsed)}")
        print(f"✅ Body: {parser.get_body_text(parsed)}")
        print(f"✅ Is unread: {parser.is_unread(parsed)}")
        
        return True
    except Exception as e:
        print(f"❌ Email parser test failed: {e}")
        return False

def test_gmail_utils():
    """Test Gmail utils functionality."""
    print("\n📧 Testing Gmail Utils...")
    
    try:
        from core.minimal_gmail_utils import MinimalGmailService
        
        service = MinimalGmailService()
        
        # Test service creation
        assert hasattr(service, 'is_authenticated')
        assert hasattr(service, 'get_messages')
        assert hasattr(service, 'get_message')
        
        print(f"✅ Gmail service created")
        print(f"✅ Authenticated: {service.is_authenticated()}")
        
        return True
    except Exception as e:
        print(f"❌ Gmail utils test failed: {e}")
        return False

def test_email_actions():
    """Test email actions functionality."""
    print("\n⚡ Testing Email Actions...")
    
    try:
        from core.minimal_email_actions import MinimalEmailActions
        
        actions = MinimalEmailActions()
        
        # Test with sample email
        sample_email = {
            "message_id": "test123",
            "headers": {
                "from": "test@example.com",
                "subject": "Test Subject"
            },
            "labels": ["UNREAD"]
        }
        
        # Test auto-reply
        result = actions.process_email(sample_email, "auto_reply")
        assert result["success"] == True
        assert result["action"] == "auto_reply"
        
        # Test stats
        stats = actions.get_stats()
        assert stats["total_processed"] > 0
        
        print(f"✅ Email actions working")
        print(f"✅ Processed: {stats['total_processed']} emails")
        
        return True
    except Exception as e:
        print(f"❌ Email actions test failed: {e}")
        return False

def test_crm_service():
    """Test CRM service functionality."""
    print("\n📊 Testing CRM Service...")
    
    try:
        from core.minimal_crm_service import MinimalCRMService
        
        crm = MinimalCRMService("data/test_crm.json")
        
        # Test adding lead
        lead = crm.add_lead("test@example.com", "Test User", "email")
        assert lead.email == "test@example.com"
        assert lead.name == "Test User"
        
        # Test finding lead
        found_lead = crm.find_lead_by_email("test@example.com")
        assert found_lead is not None
        assert found_lead.id == lead.id
        
        # Test stats
        stats = crm.get_lead_stats()
        assert stats["total_leads"] > 0
        
        print(f"✅ CRM service working")
        print(f"✅ Total leads: {stats['total_leads']}")
        
        return True
    except Exception as e:
        print(f"❌ CRM service test failed: {e}")
        return False

def test_main_cli():
    """Test main CLI functionality."""
    print("\n💻 Testing Main CLI...")
    
    try:
        # Test CLI help
        import subprocess
        result = subprocess.run([
            sys.executable, "main_minimal.py", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ CLI help command works")
        else:
            print(f"❌ CLI help failed: {result.stderr}")
            return False
        
        # Test status command
        result = subprocess.run([
            sys.executable, "main_minimal.py", "status"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ CLI status command works")
        else:
            print(f"❌ CLI status failed: {result.stderr}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False

def test_file_structure():
    """Test that all required files exist."""
    print("\n📁 Testing File Structure...")
    
    required_files = [
        "core/minimal_config.py",
        "core/minimal_auth.py",
        "core/minimal_email_parser.py",
        "core/minimal_gmail_utils.py",
        "core/minimal_email_actions.py",
        "core/minimal_crm_service.py",
        "main_minimal.py",
        "requirements_minimal.txt"
    ]
    
    missing_files = []
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} (missing)")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n❌ Missing files: {missing_files}")
        return False
    else:
        print(f"\n✅ All required files present!")
        return True

def main():
    """Run all tests."""
    print("🚀 Fikiri Solutions - Minimal Setup Test")
    print("=" * 60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Module Imports", test_imports),
        ("Configuration", test_config),
        ("Authentication", test_auth),
        ("Email Parser", test_email_parser),
        ("Gmail Utils", test_gmail_utils),
        ("Email Actions", test_email_actions),
        ("CRM Service", test_crm_service),
        ("Main CLI", test_main_cli)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Minimal setup is working correctly.")
        print("\n📝 Next steps:")
        print("1. Install dependencies: pip install -r requirements_minimal.txt")
        print("2. Run: python main_minimal.py setup")
        print("3. Run: python main_minimal.py status")
        return True
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
