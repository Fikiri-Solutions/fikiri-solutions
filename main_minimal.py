#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal Setup Script
Re-authenticates OAuth tokens to align with current Google OAuth client configuration.
"""

import sys
import os
import json
import socket
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.auth_service import setup_auth, authenticate_gmail, Authenticator
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main setup function"""
    if len(sys.argv) > 1 and sys.argv[1] == 'setup':
        logger.info("🔐 Fikiri Solutions - OAuth Re-authentication Setup")
        logger.info("=" * 60)
        logger.info("")
        logger.info("This will re-authenticate with your Google OAuth client.")
        logger.info("Make sure your .env file has the correct:")
        logger.info("  - GOOGLE_CLIENT_ID")
        logger.info("  - GOOGLE_CLIENT_SECRET")
        logger.info("  - GOOGLE_REDIRECT_URI (for local: http://localhost:5000/api/oauth/gmail/callback)")
        logger.info("")
        
        # Initialize authenticator first
        auth = Authenticator()
        
        # Check for credentials.json or environment variables
        credentials_path = Path(auth.credentials_path)
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        
        # If credentials.json doesn't exist, create it from environment variables
        if not credentials_path.exists():
            if not client_id or not client_secret:
                logger.warning("⚠️  No credentials found!")
                logger.info("")
                logger.info("You need either:")
                logger.info("  1. auth/credentials.json file (download from Google Cloud Console)")
                logger.info("  OR")
                logger.info("  2. Environment variables in .env:")
                logger.info("     GOOGLE_CLIENT_ID=your-client-id")
                logger.info("     GOOGLE_CLIENT_SECRET=your-client-secret")
                logger.info("")
                logger.info("Then run: python main_minimal.py setup")
                return False
            
            # Create credentials.json from environment variables
            logger.info("📝 Creating credentials.json from environment variables...")
            redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/api/oauth/gmail/callback')
            
            credentials_data = {
                "installed": {
                    "client_id": client_id,
                    "project_id": "fikiri-solutions",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": client_secret,
                    "redirect_uris": [
                        redirect_uri,  # API callback URI
                        "http://localhost:5000",  # For run_local_server (primary)
                        "http://localhost:8080",  # For run_local_server (fallback)
                        "http://localhost",  # Generic loopback
                        "http://127.0.0.1:5000",  # Alternative loopback
                        "http://127.0.0.1:8080"  # Alternative loopback (fallback)
                    ]
                }
            }
            
            credentials_path.parent.mkdir(parents=True, exist_ok=True)
            with open(credentials_path, 'w') as f:
                json.dump(credentials_data, f, indent=2)
            logger.info(f"✅ Created credentials.json from environment variables")
            logger.info("")
        
        # Check current status
        status = auth.get_auth_status()
        
        logger.info("📋 Current Authentication Status:")
        logger.info(f"  Credentials file: {'✅ Found' if status['credentials_file_exists'] else '❌ Missing'}")
        logger.info(f"  Token file: {'✅ Found' if status['token_file_exists'] else '❌ Missing'}")
        logger.info(f"  Authenticated: {'✅ Yes' if status['is_authenticated'] else '❌ No'}")
        logger.info("")
        
        # If token exists, ask to clear it for re-auth
        if status['token_file_exists']:
            logger.info("⚠️  Existing token found. To re-authenticate with new OAuth client:")
            logger.info("   1. Delete old token file")
            logger.info("   2. Run authentication flow")
            logger.info("")
            
            # Delete old token
            token_path = Path(auth.token_path)
            if token_path.exists():
                token_path.unlink()
                logger.info(f"✅ Deleted old token: {auth.token_path}")
                logger.info("")
        
        # Check credentials file
        if not status['credentials_file_exists']:
            logger.info("📝 Creating credentials template...")
            if auth.create_template_credentials():
                logger.info("")
                logger.info("📋 Next steps:")
                logger.info("1. Go to Google Cloud Console")
                logger.info("2. Download OAuth 2.0 credentials (JSON)")
                logger.info("3. Save as: auth/credentials.json")
                logger.info("4. Run: python main_minimal.py setup")
                return False
        
        # Run authentication
        logger.info("🔑 Starting OAuth authentication flow...")
        logger.info("")
        logger.info("This will:")
        logger.info("  1. Open your browser")
        logger.info("  2. Ask you to sign in with Google")
        logger.info("  3. Request permissions for Gmail access")
        logger.info("  4. Save the token for future use")
        logger.info("")
        
        try:
            # Perform OAuth flow using Google libraries
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            import pickle
            
            # Gmail API scopes (include 'openid' to prevent scope mismatch errors)
            SCOPES = [
                'openid',  # Google automatically adds this, so include it explicitly
                'https://www.googleapis.com/auth/gmail.modify',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile'
            ]
            
            creds = None
            # Use .pkl extension for pickle format (Google OAuth standard)
            token_path_str = auth.token_path
            if token_path_str.endswith('.json'):
                token_path_str = token_path_str.replace('.json', '.pkl')
            token_file = Path(token_path_str)
            
            # Load existing token if it exists
            if token_file.exists():
                try:
                    with open(token_file, 'rb') as token:
                        creds = pickle.load(token)
                    logger.info(f"📄 Found existing token file: {token_file}")
                except Exception as e:
                    logger.warning(f"⚠️  Could not load existing token: {e}")
            
            # If there are no (valid) credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("🔄 Refreshing expired token...")
                    creds.refresh(Request())
                else:
                    logger.info("🔑 Starting OAuth flow...")
                    logger.info("   This will open your browser for authentication")
                    logger.info("")
                    
                    # Load credentials from file
                    credentials_path = Path(auth.credentials_path)
                    if not credentials_path.exists():
                        logger.error(f"❌ Credentials file not found: {auth.credentials_path}")
                        logger.info("   Please download OAuth credentials from Google Cloud Console")
                        logger.info("   and save as: auth/credentials.json")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(credentials_path), SCOPES
                    )
                    # Try port 5000 first, fallback to 8080 if in use
                    # Make sure both ports are in Google Console's Authorized redirect URIs
                    oauth_port = 5000
                    try:
                        # Check if port is available
                        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        test_socket.settimeout(1)
                        result = test_socket.connect_ex(('localhost', oauth_port))
                        test_socket.close()
                        if result == 0:
                            # Port is in use, try 8080
                            logger.info(f"⚠️  Port {oauth_port} is in use, trying port 8080...")
                            oauth_port = 8080
                    except Exception:
                        pass
                    
                    logger.info(f"🔑 Using port {oauth_port} for OAuth callback...")
                    creds = flow.run_local_server(port=oauth_port)
                    logger.info("✅ OAuth flow completed")
                
                # Save the credentials for the next run
                token_file.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with open(token_file, 'wb') as token:
                        pickle.dump(creds, token)
                    logger.info(f"💾 Token saved to: {token_file}")
                    logger.info(f"   File size: {token_file.stat().st_size} bytes")
                except Exception as e:
                    logger.error(f"❌ Failed to save token: {e}")
                    raise
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ Authentication successful!")
            logger.info("")
            logger.info("Your OAuth token has been saved and is ready to use.")
            logger.info("Token cache is now aligned with your OAuth client configuration.")
            logger.info("")
            logger.info("You can now run: python app.py")
            return True
                
        except Exception as e:
            logger.error(f"❌ Error during authentication: {e}")
            logger.info("")
            logger.info("Troubleshooting:")
            logger.info("  1. Verify GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")
            logger.info("  2. In Google Cloud Console → Credentials → Your OAuth Client:")
            logger.info("     Add these EXACT redirect URIs (case-sensitive, trailing slash matters):")
            logger.info("     - http://localhost:5000")
            logger.info("     - http://localhost:5000/")
            logger.info("     - http://localhost:8080")
            logger.info("     - http://localhost:8080/")
            logger.info("     - http://localhost")
            logger.info("     - http://127.0.0.1:5000")
            logger.info("     - http://127.0.0.1:8080")
            logger.info("  3. The script will automatically use port 8080 if 5000 is in use")
            logger.info("  4. Wait a few seconds after saving URIs in Google Console for changes to propagate")
            logger.info("  5. Ensure credentials.json is valid")
            return False
    
    else:
        logger.info("Usage: python main_minimal.py setup")
        logger.info("")
        logger.info("This will re-authenticate OAuth tokens with your current Google OAuth client.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

