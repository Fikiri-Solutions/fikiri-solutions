#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal Authentication Service
Lightweight authentication without heavy Google API dependencies.
"""

import os
import json
import pickle
from pathlib import Path
from typing import Optional, Dict, Any

class MinimalAuthenticator:
    """Minimal authentication handler - lightweight version."""
    
    def __init__(self, credentials_path: str = "auth/credentials.json", token_path: str = "auth/token.pkl"):
        """Initialize minimal authenticator."""
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.credentials = None
        self.token = None
    
    def check_credentials_file(self) -> bool:
        """Check if credentials file exists and is valid."""
        creds_file = Path(self.credentials_path)
        if not creds_file.exists():
            print(f"❌ Credentials file not found: {self.credentials_path}")
            return False
        
        try:
            with open(creds_file, 'r') as f:
                creds_data = json.load(f)
            
            # Basic validation
            if "installed" not in creds_data and "web" not in creds_data:
                print("❌ Invalid credentials file format")
                return False
            
            print("✅ Credentials file found and valid")
            return True
            
        except Exception as e:
            print(f"❌ Error reading credentials file: {e}")
            return False
    
    def check_token_file(self) -> bool:
        """Check if token file exists."""
        token_file = Path(self.token_path)
        if token_file.exists():
            print("✅ Token file found")
            return True
        else:
            print("❌ Token file not found - authentication needed")
            return False
    
    def load_token(self) -> Optional[Dict[str, Any]]:
        """Load token from file."""
        token_file = Path(self.token_path)
        if not token_file.exists():
            return None
        
        try:
            with open(token_file, 'rb') as f:
                token = pickle.load(f)
            print("✅ Token loaded successfully")
            return token
        except Exception as e:
            print(f"❌ Error loading token: {e}")
            return None
    
    def save_token(self, token: Dict[str, Any]) -> bool:
        """Save token to file."""
        try:
            # Ensure auth directory exists
            auth_dir = Path(self.token_path).parent
            auth_dir.mkdir(exist_ok=True)
            
            with open(self.token_path, 'wb') as f:
                pickle.dump(token, f)
            print("✅ Token saved successfully")
            return True
        except Exception as e:
            print(f"❌ Error saving token: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        if not self.check_credentials_file():
            return False
        
        token = self.load_token()
        if token is None:
            return False
        
        # Check if token is valid (has required attributes)
        try:
            # If it's a Google Credentials object, check for valid attributes
            if hasattr(token, 'token') and hasattr(token, 'refresh_token'):
                print("✅ Authentication valid")
                return True
            # If it's a dictionary, check for required fields
            elif isinstance(token, dict):
                required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret']
                if all(field in token for field in required_fields):
                    print("✅ Authentication valid")
                    return True
            else:
                print("❌ Invalid token format")
                return False
        except Exception as e:
            print(f"❌ Error validating token: {e}")
            return False
        
        return False
    
    def get_auth_status(self) -> Dict[str, Any]:
        """Get comprehensive authentication status."""
        status = {
            "credentials_file_exists": self.check_credentials_file(),
            "token_file_exists": self.check_token_file(),
            "is_authenticated": False,
            "needs_setup": False
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
            print(f"✅ Template credentials created at {self.credentials_path}")
            print("📝 Please edit the file with your actual Gmail API credentials")
            return True
        except Exception as e:
            print(f"❌ Error creating template: {e}")
            return False

def authenticate_gmail(credentials_path: str = "auth/credentials.json", token_path: str = "auth/token.pkl") -> bool:
    """Simple authentication check function."""
    auth = MinimalAuthenticator(credentials_path, token_path)
    return auth.is_authenticated()

def setup_auth() -> bool:
    """Setup authentication - create template and check status."""
    print("🔐 Fikiri Solutions - Authentication Setup")
    print("=" * 50)
    
    auth = MinimalAuthenticator()
    
    # Check current status
    status = auth.get_auth_status()
    
    if status["is_authenticated"]:
        print("✅ Authentication is already set up!")
        return True
    
    if not status["credentials_file_exists"]:
        print("📝 Creating credentials template...")
        if auth.create_template_credentials():
            print("\n📋 Next steps:")
            print("1. Go to Google Cloud Console")
            print("2. Create a new project or select existing one")
            print("3. Enable Gmail API")
            print("4. Create OAuth 2.0 credentials")
            print("5. Download credentials and replace the template file")
            print("6. Run authentication again")
        return False
    
    if not status["token_file_exists"]:
        print("🔑 Ready for authentication!")
        print("📋 Next steps:")
        print("1. Make sure your credentials.json is properly configured")
        print("2. Run the authentication process")
        return False
    
    return False

if __name__ == "__main__":
    setup_auth()
