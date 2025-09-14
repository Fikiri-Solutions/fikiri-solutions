#!/usr/bin/env python3
"""
Fikiri Solutions - Setup Script

This script helps you set up the Fikiri Solutions Gmail Lead Responder
by guiding you through the initial configuration and authentication.
"""

import os
import sys
import shutil
from pathlib import Path


def main():
    """Main setup function."""
    print("🚀 Fikiri Solutions - Gmail Lead Responder Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("main.py"):
        print("❌ Error: Please run this script from the Fikiri project root directory")
        sys.exit(1)
    
    print("✅ Found Fikiri project files")
    
    # Check for credentials
    credentials_path = "auth/credentials.json"
    if not os.path.exists(credentials_path):
        print(f"\n📋 Setting up authentication...")
        print(f"1. Go to Google Cloud Console: https://console.cloud.google.com/")
        print(f"2. Create a new project or select existing one")
        print(f"3. Enable the Gmail API")
        print(f"4. Create OAuth2 credentials (Desktop application)")
        print(f"5. Download the credentials JSON file")
        print(f"6. Save it as: {credentials_path}")
        print(f"\n📄 Template file created: auth/credentials.json.template")
        
        # Create credentials template
        template_path = "auth/credentials.json.template"
        if os.path.exists(template_path):
            print(f"✅ Template file already exists")
        else:
            print(f"❌ Template file missing - please check the auth/ directory")
    else:
        print(f"✅ Found credentials file: {credentials_path}")
    
    # Check for environment file
    env_path = ".env"
    env_example_path = "env.example"
    
    if not os.path.exists(env_path):
        if os.path.exists(env_example_path):
            print(f"\n📋 Setting up environment variables...")
            print(f"1. Copy {env_example_path} to {env_path}")
            print(f"2. Edit {env_path} with your actual values")
            
            # Offer to copy the example
            response = input(f"\nWould you like to copy {env_example_path} to {env_path}? (y/n): ")
            if response.lower() in ['y', 'yes']:
                shutil.copy(env_example_path, env_path)
                print(f"✅ Created {env_path} from template")
                print(f"📝 Please edit {env_path} with your actual values")
        else:
            print(f"❌ Environment template missing: {env_example_path}")
    else:
        print(f"✅ Found environment file: {env_path}")
    
    # Check Python dependencies
    print(f"\n📦 Checking Python dependencies...")
    try:
        import google.auth
        import google.auth.oauthlib
        import googleapiclient.discovery
        import bs4
        print("✅ All required dependencies are installed")
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print(f"📦 Run: pip3 install -r requirements.txt")
        return
    
    # Test CLI
    print(f"\n🧪 Testing CLI...")
    try:
        import subprocess
        result = subprocess.run([sys.executable, "main.py", "status"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ CLI is working correctly")
            print("📊 Current status:")
            print(result.stdout)
        else:
            print(f"⚠️ CLI test failed: {result.stderr}")
    except Exception as e:
        print(f"❌ CLI test error: {e}")
    
    # Next steps
    print(f"\n🎯 Next Steps:")
    print(f"1. Set up Google OAuth2 credentials (if not done)")
    print(f"2. Run: python3 main.py auth")
    print(f"3. Test with: python3 main.py --dry-run fetch")
    print(f"4. Process emails: python3 main.py --dry-run process")
    
    print(f"\n📚 Documentation:")
    print(f"• README.md - Complete setup and usage guide")
    print(f"• templates/ - Email response templates")
    print(f"• tests/ - Test suite for validation")
    
    print(f"\n🚀 You're ready to automate your Gmail workflows!")


if __name__ == '__main__':
    main()
