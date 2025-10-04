#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal Authentication Service
Lightweight authentication without heavy Google API dependencies.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

# Initialize logger
logger = logging.getLogger(__name__)

class MinimalAuthenticator:
    """Minimal authentication handler - lightweight version."""
    
    def __init__(self, credentials_path: str = None, token_path: str = None):
        """Initialize minimal authenticator with environment isolation."""
        # Environment isolation for token files
        env_suffix = os.getenv("FLASK_ENV", "dev")
        
        self.credentials_path = credentials_path or "auth/credentials.json"
        self.token_path = token_path or f"auth/token_{env_suffix}.json"
        self.credentials = None
        self.token = None
    
    def check_credentials_file(self) -> bool:
        """Check if credentials file exists and is valid."""
        creds_file = Path(self.credentials_path)
        if not creds_file.exists():
            logger.error(f"❌ Credentials file not found: {self.credentials_path}")
            return False
        
        try:
            with open(creds_file, 'r') as f:
                creds_data = json.load(f)
            
            # Basic validation
            if "installed" not in creds_data and "web" not in creds_data:
                logger.warning("❌ Invalid credentials file format")
                return False
            
            logger.info("✅ Credentials file found and valid")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error reading credentials file: {e}")
            return False
    
    def check_token_file(self, verbose: bool = False) -> bool:
        """Check if token file exists."""
        token_file = Path(self.token_path)
        if token_file.exists():
            if verbose:
                logger.info("✅ Token file found")
            return True
        else:
            if verbose:
                logger.info("❌ Token file not found - authentication needed")
            return False
    
    def load_token(self) -> Optional[Dict[str, Any]]:
        """Load token from JSON file."""
        token_file = Path(self.token_path)
        if not token_file.exists():
            return None
        
        try:
            with open(token_file, 'r') as f:
                token = json.load(f)
            logger.info("✅ Token loaded successfully")
            return token
        except Exception as e:
            logger.error(f"❌ Error loading token: {e}")
            return None
    
    def save_token(self, token: Dict[str, Any]) -> bool:
        """Save token to JSON file."""
        try:
            # Ensure auth directory exists
            auth_dir = Path(self.token_path).parent
            auth_dir.mkdir(exist_ok=True)
            
            with open(self.token_path, 'w') as f:
                json.dump(token, f, indent=2)
            logger.info("✅ Token saved successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Error saving token: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated with token expiration handling."""
        if not self.check_credentials_file():
            return False
        
        token = self.load_token()
        if token is None:
            return False
        
        # Check if token is valid (has required attributes)
        try:
            # If it's a Google Credentials object, check for valid attributes
            if hasattr(token, 'token') and hasattr(token, 'refresh_token'):
                logger.info("✅ Authentication valid")
                return True
            # If it's a dictionary, check for required fields and expiration
            elif isinstance(token, dict):
                required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret']
                if all(field in token for field in required_fields):
                    # Check token expiration
                    expiry = token.get('expiry')
                    if expiry:
                        try:
                            expiry_dt = datetime.fromisoformat(expiry)
                            if expiry_dt < datetime.utcnow():
                                logger.warning("⚠️ Token expired")
                                return False
                        except ValueError:
                            logger.warning("⚠️ Invalid token expiry format")
                    
                    logger.info("✅ Authentication valid")
                    return True
            else:
                logger.error("❌ Invalid token format")
                return False
        except Exception as e:
            logger.error(f"❌ Error validating token: {e}")
            return False
        
        return False
    
    def clear_token(self) -> bool:
        """Clear stored token to trigger re-authentication."""
        token_file = Path(self.token_path)
        if token_file.exists():
            try:
                token_file.unlink()
                logger.info("🧹 Token cleared — new authentication required.")
                return True
            except Exception as e:
                logger.error(f"❌ Error clearing token: {e}")
                return False
        else:
            logger.info("ℹ️ No token file to clear")
            return True
    
    def get_auth_status(self) -> Dict[str, Any]:
        """Get comprehensive authentication status."""
        status = {
            "credentials_file_exists": self.check_credentials_file(),
            "token_file_exists": self.check_token_file(),
            "is_authenticated": False,
            "needs_setup": False,
            "token_path": self.token_path,
            "environment": os.getenv("FLASK_ENV", "dev")
        }
        
        if status["credentials_file_exists"] and status["token_file_exists"]:
            status["is_authenticated"] = self.is_authenticated()
        
        if not status["credentials_file_exists"]:
            status["needs_setup"] = True
            status["setup_message"] = f"Please add your Gmail API credentials to {self.credentials_path}"
        elif not status["token_file_exists"]:
            status["needs_setup"] = True
            status["setup_message"] = "Please run authentication to get access token"
        
        return status
    
    def create_template_credentials(self) -> bool:
        """Create a template credentials file."""
        template_file = Path(self.credentials_path)
        template_dir = template_file.parent
        template_dir.mkdir(exist_ok=True)
        
        template_data = {
            "installed": {
                "client_id": "YOUR_CLIENT_ID_HERE",
                "project_id": "YOUR_PROJECT_ID_HERE",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "YOUR_CLIENT_SECRET_HERE",
                "redirect_uris": ["http://localhost"]
            }
        }
        
        try:
            with open(template_file, 'w') as f:
                json.dump(template_data, f, indent=2)
            logger.info(f"✅ Template credentials created at {self.credentials_path}")
            logger.info("📝 Please edit the file with your actual Gmail API credentials")
            return True
        except Exception as e:
            logger.error(f"❌ Error creating template: {e}")
            return False

def authenticate_gmail(credentials_path: str = None, token_path: str = None) -> bool:
    """Simple authentication check function with environment isolation."""
    auth = MinimalAuthenticator(credentials_path, token_path)
    return auth.is_authenticated()

def setup_auth() -> bool:
    """Setup authentication - create template and check status."""
    logger.info("🔐 Fikiri Solutions - Authentication Setup")
    logger.info("=" * 50)
    
    auth = MinimalAuthenticator()
    
    # Check current status
    status = auth.get_auth_status()
    
    if status["is_authenticated"]:
        logger.info("✅ Authentication is already set up!")
        return True
    
    if not status["credentials_file_exists"]:
        logger.info("📝 Creating credentials template...")
        if auth.create_template_credentials():
            logger.info("\n📋 Next steps:")
            logger.info("1. Go to Google Cloud Console")
            logger.info("2. Create a new project or select existing one")
            logger.info("3. Enable Gmail API")
            logger.info("4. Create OAuth 2.0 credentials")
            logger.info("5. Download credentials and replace the template file")
            logger.info("6. Run authentication again")
        return False
    
    if not status["token_file_exists"]:
        logger.info("🔑 Ready for authentication!")
        logger.info("📋 Next steps:")
        logger.info("1. Make sure your credentials.json is properly configured")
        logger.info("2. Run the authentication process")
        return False
    
    return False

if __name__ == "__main__":
    setup_auth()
