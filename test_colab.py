#!/usr/bin/env python3
"""
Fikiri Solutions - Google Colab Test Script
Quick test script to verify the system works in Google Colab environment.
"""

import os
import sys
import subprocess
from pathlib import Path

def test_installation():
    """Test if the system is properly installed."""
    print("🧪 Testing Fikiri Solutions Installation...")
    print("=" * 50)
    
    # Check Python version
    print(f"✅ Python version: {sys.version}")
    
    # Check if we're in the right directory
    current_dir = Path.cwd()
    print(f"✅ Current directory: {current_dir}")
    
    # Check if main.py exists
    main_py = current_dir / "main.py"
    if main_py.exists():
        print("✅ main.py found")
    else:
        print("❌ main.py not found")
        return False
    
    # Check if requirements.txt exists
    requirements = current_dir / "requirements.txt"
    if requirements.exists():
        print("✅ requirements.txt found")
    else:
        print("❌ requirements.txt not found")
        return False
    
    return True

def test_cli_help():
    """Test if the CLI help command works."""
    print("\n🔍 Testing CLI Help Command...")
    print("=" * 50)
    
    try:
        result = subprocess.run(
            [sys.executable, "main.py", "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ CLI help command works!")
            print("📋 Available commands:")
            # Extract command names from help output
            lines = result.stdout.split('\n')
            for line in lines:
                if 'auth' in line or 'list' in line or 'process' in line or 'crm' in line:
                    print(f"   {line.strip()}")
        else:
            print(f"❌ CLI help failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ CLI help command timed out")
        return False
    except Exception as e:
        print(f"❌ CLI help command error: {e}")
        return False
    
    return True

def test_imports():
    """Test if core modules can be imported."""
    print("\n📦 Testing Core Module Imports...")
    print("=" * 50)
    
    # Test basic Python imports
    try:
        import json
        import logging
        import argparse
        print("✅ Basic Python modules imported successfully")
    except ImportError as e:
        print(f"❌ Basic Python import failed: {e}")
        return False
    
    # Test if we can import from main.py
    try:
        # Add current directory to path
        sys.path.insert(0, str(Path.cwd()))
        
        # Try to import main module
        import main
        print("✅ main.py imported successfully")
    except ImportError as e:
        print(f"❌ main.py import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error importing main.py: {e}")
        return False
    
    return True

def test_file_structure():
    """Test if the expected file structure exists."""
    print("\n📁 Testing File Structure...")
    print("=" * 50)
    
    expected_files = [
        "main.py",
        "requirements.txt",
        "README.md",
        "Dockerfile",
        "docker-compose.yml",
        "auth/credentials.json.template",
        "templates/general_response.txt",
        "data/business_profile.json",
        "data/faq_knowledge.json"
    ]
    
    missing_files = []
    for file_path in expected_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} (missing)")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n⚠️  Missing files: {len(missing_files)}")
        return False
    else:
        print(f"\n✅ All expected files present!")
        return True

def main():
    """Run all tests."""
    print("🚀 Fikiri Solutions - Google Colab Test Suite")
    print("=" * 60)
    
    tests = [
        ("Installation Check", test_installation),
        ("File Structure", test_file_structure),
        ("Module Imports", test_imports),
        ("CLI Help Command", test_cli_help)
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
    print("\n📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The system is ready to use.")
        print("\n📝 Next steps:")
        print("1. Set up Gmail API credentials")
        print("2. Run: python main.py auth")
        print("3. Test with: python main.py list --query 'is:unread' --max 5")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure you're in the correct directory")
        print("2. Check if all files were downloaded properly")
        print("3. Try: pip install -r requirements.txt")

if __name__ == "__main__":
    main()
