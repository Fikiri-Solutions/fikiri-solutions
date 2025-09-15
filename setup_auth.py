#!/usr/bin/env python3
"""
Fikiri Solutions - Gmail Authentication Setup Helper
"""

import json
import os
from pathlib import Path

def setup_gmail_auth():
    """Interactive Gmail authentication setup."""
    print("🔐 Fikiri Solutions - Gmail Authentication Setup")
    print("=" * 50)
    
    # Check if credentials file exists
    credentials_path = Path("auth/credentials.json")
    
    if credentials_path.exists():
        print("✅ Gmail credentials file found!")
        try:
            with open(credentials_path, 'r') as f:
                creds = json.load(f)
            
            client_id = creds.get('installed', {}).get('client_id', 'Not found')
            if 'YOUR_CLIENT_ID_HERE' in client_id:
                print("❌ Credentials file contains placeholder values")
                print("   Please replace with actual Google Cloud credentials")
                return False
            else:
                print(f"✅ Client ID: {client_id[:20]}...")
                return True
                
        except Exception as e:
            print(f"❌ Error reading credentials: {e}")
            return False
    else:
        print("❌ No Gmail credentials file found")
        print("\n📋 To get Gmail API credentials:")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Create/select a project")
        print("3. Enable Gmail API")
        print("4. Create OAuth 2.0 credentials (Desktop Application)")
        print("5. Download JSON file")
        print("6. Rename to 'credentials.json' and place in auth/ directory")
        return False

def check_openai_key():
    """Check if OpenAI API key is set."""
    print("\n🤖 OpenAI API Key Check")
    print("=" * 30)
    
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        if api_key.startswith('sk-'):
            print(f"✅ OpenAI API key found: {api_key[:20]}...")
            return True
        else:
            print("❌ OpenAI API key format invalid")
            return False
    else:
        print("❌ No OpenAI API key found")
        print("\n📋 To set OpenAI API key:")
        print("export OPENAI_API_KEY='sk-your-key-here'")
        return False

def main():
    """Main setup function."""
    print("🚀 Fikiri Solutions - Authentication Status")
    print("=" * 50)
    
    gmail_ok = setup_gmail_auth()
    openai_ok = check_openai_key()
    
    print("\n📊 Status Summary:")
    print(f"Gmail API: {'✅ Ready' if gmail_ok else '❌ Needs Setup'}")
    print(f"OpenAI API: {'✅ Ready' if openai_ok else '❌ Needs Setup'}")
    
    if gmail_ok and openai_ok:
        print("\n🎉 All authentication ready!")
        print("You can now run: python app.py")
    else:
        print("\n⚠️  Complete the setup above, then run this script again")

if __name__ == "__main__":
    main()
