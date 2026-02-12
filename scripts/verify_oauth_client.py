#!/usr/bin/env python3
"""
Verify OAuth client configuration
Checks if the client ID in .env matches credentials.json and helps identify issues
"""
import json
from pathlib import Path

def load_env_file():
    """Load .env file manually"""
    env_path = Path(".env")
    if not env_path.exists():
        return {}
    
    env_vars = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    return env_vars

def main():
    print("🔍 OAuth Client Verification")
    print("=" * 60)
    print("")
    
    # Load .env
    env_vars = load_env_file()
    env_client_id = env_vars.get('GOOGLE_CLIENT_ID', 'NOT SET')
    env_client_secret = env_vars.get('GOOGLE_CLIENT_SECRET', 'NOT SET')
    
    print("📋 From .env file:")
    if env_client_id != 'NOT SET':
        print(f"   Client ID: {env_client_id[:30]}...{env_client_id[-10:]}")
    else:
        print("   ❌ GOOGLE_CLIENT_ID: NOT SET")
    
    if env_client_secret != 'NOT SET':
        print(f"   Client Secret: {'*' * 20}...{env_client_secret[-4:]}")
    else:
        print("   ❌ GOOGLE_CLIENT_SECRET: NOT SET")
    print("")
    
    # Check credentials.json
    creds_file = Path("auth/credentials.json")
    if creds_file.exists():
        with open(creds_file) as f:
            creds_data = json.load(f)
        
        creds_client_id = creds_data.get('installed', {}).get('client_id', 'NOT FOUND')
        creds_client_secret = creds_data.get('installed', {}).get('client_secret', 'NOT FOUND')
        
        print("📋 From auth/credentials.json:")
        if creds_client_id != 'NOT FOUND':
            print(f"   Client ID: {creds_client_id[:30]}...{creds_client_id[-10:]}")
        else:
            print("   ❌ Client ID: NOT FOUND")
        
        if creds_client_secret != 'NOT FOUND':
            print(f"   Client Secret: {'*' * 20}...{creds_client_secret[-4:]}")
        else:
            print("   ❌ Client Secret: NOT FOUND")
        print("")
        
        # Compare
        if env_client_id != 'NOT SET' and creds_client_id != 'NOT FOUND':
            if env_client_id == creds_client_id:
                print("✅ Client IDs match between .env and credentials.json")
            else:
                print("⚠️  Client IDs DO NOT MATCH!")
                print("   This could cause 'deleted_client' errors.")
                print("")
                print("   To fix:")
                print("   1. Make sure your .env has the NEW client ID from Google Cloud Console")
                print("   2. Run: python3 scripts/sync_oauth_from_env.py")
                print("   3. Delete any old token files: rm -f auth/token*.pkl")
                print("   4. Run: python3 main_minimal.py setup")
    else:
        print("❌ auth/credentials.json not found")
        print("")
        print("   To create it:")
        print("   1. Make sure .env has GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET")
        print("   2. Run: python3 scripts/sync_oauth_from_env.py")
    
    print("")
    print("=" * 60)
    print("")
    print("💡 If you're getting 'deleted_client' errors:")
    print("   1. Go to Google Cloud Console → APIs & Services → Credentials")
    print("   2. Find your OAuth 2.0 Client ID")
    print("   3. Copy the NEW client ID and secret")
    print("   4. Update .env with the NEW values")
    print("   5. Run: python3 scripts/sync_oauth_from_env.py")
    print("   6. Delete old tokens: rm -f auth/token*.pkl")
    print("   7. Run: python3 main_minimal.py setup")

if __name__ == "__main__":
    main()

