#!/usr/bin/env python3
"""
Sync OAuth credentials from .env to credentials.json
"""
import json
import os
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
    print("🔄 Syncing OAuth credentials from .env to credentials.json...")
    print("")
    
    # Load .env
    env_vars = load_env_file()
    new_client_id = env_vars.get('GOOGLE_CLIENT_ID')
    new_client_secret = env_vars.get('GOOGLE_CLIENT_SECRET')
    
    if not new_client_id or not new_client_secret:
        print("❌ GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not found in .env")
        return False
    
    print(f"📋 New Client ID from .env: {new_client_id[:40]}...")
    
    # Read current credentials.json
    creds_file = Path("auth/credentials.json")
    if not creds_file.exists():
        print("❌ credentials.json not found")
        return False
    
    with open(creds_file) as f:
        current_data = json.load(f)
    
    current_client_id = current_data.get('installed', {}).get('client_id', '')
    print(f"📋 Current Client ID: {current_client_id[:40]}...")
    
    if current_client_id == new_client_id:
        print("✅ credentials.json already has the correct client ID")
        return True
    
    print("⚠️  Client IDs don't match - updating credentials.json...")
    
    # Update with new credentials
    current_data['installed']['client_id'] = new_client_id
    current_data['installed']['client_secret'] = new_client_secret
    
    # Ensure auth directory exists
    creds_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(creds_file, 'w') as f:
        json.dump(current_data, f, indent=2)
    
    print("✅ Updated credentials.json with new client ID and secret")
    print("")
    print("🧹 Cleaning old tokens...")
    for token_file in creds_file.parent.glob("token*.pkl"):
        token_file.unlink()
        print(f"   Deleted: {token_file}")
    for token_file in creds_file.parent.glob("token*.json"):
        token_file.unlink()
        print(f"   Deleted: {token_file}")
    
    print("")
    print("✅ Ready! Now run: python main_minimal.py setup")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

