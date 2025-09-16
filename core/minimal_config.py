#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal Configuration
Lightweight configuration management without heavy dependencies.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

class MinimalConfig:
    """Minimal configuration class - no dataclasses, no heavy imports."""
    
    def __init__(self):
        """Initialize with default values."""
        # Gmail settings
        self.gmail_credentials_path = "auth/credentials.json"
        self.gmail_token_path = "auth/token.pkl"
        self.gmail_scopes = ["https://www.googleapis.com/auth/gmail.modify"]
        self.gmail_user_id = "me"
        self.gmail_max_results = 10
        
        # Email settings
        self.auto_reply_enabled = False
        self.reply_template = ""
        self.signature = ""
        
        # Logging settings
        self.log_level = "INFO"
        self.log_file = None
        
        # General settings
        self.debug = False
        self.dry_run = False
        
        # Load from environment
        self._load_from_env()
        
        # Load from config file if exists
        self._load_from_file()
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
        self.gmail_credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH", self.gmail_credentials_path)
        self.gmail_token_path = os.getenv("GMAIL_TOKEN_PATH", self.gmail_token_path)
        try:
            self.gmail_max_results = int(os.getenv("GMAIL_MAX_RESULTS", str(self.gmail_max_results)))
        except ValueError:
            print(f"⚠️ Invalid GMAIL_MAX_RESULTS value, using default: {self.gmail_max_results}")
        self.auto_reply_enabled = os.getenv("AUTO_REPLY_ENABLED", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
    
    def _load_from_file(self):
        """Load configuration from config.json if it exists."""
        config_file = Path("config.json")
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    # Update settings from file
                    for key, value in data.items():
                        if hasattr(self, key):
                            setattr(self, key, value)
            except Exception as e:
                print(f"Warning: Could not load config.json: {e}")
    
    def save(self):
        """Save current configuration to config.json."""
        config_file = Path("config.json")
        try:
            config_data = {
                "gmail_credentials_path": self.gmail_credentials_path,
                "gmail_token_path": self.gmail_token_path,
                "gmail_max_results": self.gmail_max_results,
                "auto_reply_enabled": self.auto_reply_enabled,
                "reply_template": self.reply_template,
                "signature": self.signature,
                "log_level": self.log_level,
                "debug": self.debug,
                "dry_run": self.dry_run
            }
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            print("✅ Configuration saved to config.json")
        except Exception as e:
            print(f"❌ Could not save config.json: {e}")
    
    def get_gmail_scopes(self):
        """Get Gmail scopes as list."""
        return self.gmail_scopes
    
    def is_debug(self):
        """Check if debug mode is enabled."""
        return self.debug
    
    def is_dry_run(self):
        """Check if dry run mode is enabled."""
        return self.dry_run

# Global config instance
_config: Optional[MinimalConfig] = None

def get_config() -> MinimalConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = MinimalConfig()
    return _config

# Default templates
DEFAULT_REPLY_TEMPLATE = """Hi {sender_name},

Thank you for your email regarding "{subject}".

I have received your message and will get back to you as soon as possible.

Best regards,
Fikiri Solutions Team"""

DEFAULT_SIGNATURE = """

---
Fikiri Solutions
Automated Response System"""
