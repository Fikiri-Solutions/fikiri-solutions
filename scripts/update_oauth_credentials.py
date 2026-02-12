#!/usr/bin/env python3
"""
Update OAuth credentials from downloaded JSON file
"""
import json
import sys
from pathlib import Path

def update_credentials(new_creds_file, target_file="auth/credentials.json"):
    """Update credentials.json with new OAuth client"""
    try:
        # Read new credentials file
        with open(new_creds_file, 'r') as f:
            new_creds = json.load(f)
        
        # Handle both 'web' and 'installed' formats
        if 'web' in new_creds:
            web_creds = new_creds['web']
            # Convert to 'installed' format for local use
            installed_format = {
                "installed": {
                    "client_id": web_creds.get('client_id'),
                    "project_id": web_creds.get('project_id', 'fikiri-solutions'),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": web_creds.get('client_secret'),
                    "redirect_uris": web_creds.get('redirect_uris', ['http://localhost'])
                }
            }
        elif 'installed' in new_creds:
            installed_format = new_creds
        else:
            print("❌ Invalid credentials format. Expected 'web' or 'installed' key.")
            return False
        
        # Ensure auth directory exists
        target_path = Path(target_file)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write updated credentials
        with open(target_path, 'w') as f:
            json.dump(installed_format, f, indent=2)
        
        client_id = installed_format['installed']['client_id']
        print(f"✅ Updated credentials.json")
        print(f"   Client ID: {client_id[:30]}...")
        print(f"   Location: {target_path.absolute()}")
        return True
        
    except FileNotFoundError:
        print(f"❌ File not found: {new_creds_file}")
        print("   Please provide the path to your downloaded OAuth credentials JSON file")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/update_oauth_credentials.py <path-to-downloaded-credentials.json>")
        print("")
        print("Example:")
        print("  python scripts/update_oauth_credentials.py ~/Downloads/client_secret_*.json")
        sys.exit(1)
    
    new_file = sys.argv[1]
    if update_credentials(new_file):
        print("")
        print("✅ Credentials updated! Now run:")
        print("   python main_minimal.py setup")
    else:
        sys.exit(1)
