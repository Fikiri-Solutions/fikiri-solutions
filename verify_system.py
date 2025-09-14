#!/usr/bin/env python3
"""
Fikiri System Verification Script
Run this in any working Python environment to test the system
"""

import sys
import os
from pathlib import Path

def verify_files():
    """Verify all essential files exist."""
    print("🔍 Verifying File Structure...")
    
    essential_files = [
        "main.py",
        "requirements.txt",
        "core/simple_chatbot.py",
        "core/vector_db.py", 
        "core/auth.py",
        "core/email_parser.py",
        "core/gmail_utils.py",
        "core/actions.py",
        "core/config.py",
        "core/crm_service.py",
        "core/crm_followups.py",
        "auth/credentials.json.template",
        "templates/general_response.txt",
        "data/faq_knowledge.json",
        "data/business_profile.json"
    ]
    
    missing_files = []
    for file_path in essential_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
        else:
            print(f"✅ {file_path}")
    
    if missing_files:
        print(f"\n❌ Missing files: {missing_files}")
        return False
    else:
        print("\n✅ All essential files present!")
        return True

def test_imports():
    """Test core imports."""
    print("\n🧪 Testing Core Imports...")
    
    tests = [
        ("core.simple_chatbot", "Simple Chatbot"),
        ("core.vector_db", "Vector Database"),
        ("core.auth", "Gmail Auth"),
        ("core.email_parser", "Email Parser"),
        ("core.gmail_utils", "Gmail Utils"),
        ("core.actions", "Email Actions"),
        ("core.config", "Config"),
        ("core.crm_service", "CRM Service"),
    ]
    
    results = []
    for module, name in tests:
        try:
            __import__(module)
            print(f"✅ {name}")
            results.append(True)
        except Exception as e:
            print(f"❌ {name}: {str(e)[:50]}...")
            results.append(False)
    
    return all(results)

def test_chatbot():
    """Test chatbot functionality."""
    print("\n🤖 Testing Chatbot...")
    
    try:
        from core.simple_chatbot import chatbot_engine
        
        # Test basic response
        response = chatbot_engine.generate_response("Hello")
        print(f"✅ Chatbot response: {response[:50]}...")
        
        # Test stats
        stats = chatbot_engine.get_stats()
        print(f"✅ Chatbot stats: {stats}")
        
        return True
    except Exception as e:
        print(f"❌ Chatbot test failed: {e}")
        return False

def test_cli():
    """Test CLI help command."""
    print("\n💻 Testing CLI...")
    
    try:
        import subprocess
        result = subprocess.run([sys.executable, "main.py", "--help"], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ CLI help command works")
            return True
        else:
            print(f"❌ CLI failed: {result.stderr[:100]}...")
            return False
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Fikiri System Verification")
    print("=" * 50)
    
    tests = [
        ("File Structure", verify_files),
        ("Core Imports", test_imports),
        ("Chatbot", test_chatbot),
        ("CLI", test_cli)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! System is ready to use.")
    else:
        print("⚠️  Some tests failed. Check the output above.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

