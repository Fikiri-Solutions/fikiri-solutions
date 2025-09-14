#!/usr/bin/env python3
"""
Fikiri Solutions - Minimal Configuration
Simple configuration management for the cleaned codebase.
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

@dataclass
class GmailConfig:
    """Gmail API configuration."""
    credentials_path: str = "auth/credentials.json"
    token_path: str = "auth/token.pkl"
    scopes: list = None
    user_id: str = "me"
    max_results: int = 10
    batch_size: int = 100
    
    def __post_init__(self):
        if self.scopes is None:
            self.scopes = ["https://www.googleapis.com/auth/gmail.modify"]

@dataclass
class EmailConfig:
    """Email processing configuration."""
    auto_reply_enabled: bool = False
    reply_template: str = ""
    signature: str = ""
    max_attachments: int = 5
    supported_mime_types: list = None
    
    def __post_init__(self):
        if self.supported_mime_types is None:
            self.supported_mime_types = [
                "text/plain",
                "text/html",
                "multipart/alternative",
                "multipart/mixed",
                "multipart/related"
            ]

@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5

@dataclass
class Config:
    """Main configuration class."""
    gmail: GmailConfig = None
    email: EmailConfig = None
    logging: LoggingConfig = None
    debug: bool = False
    dry_run: bool = False
    
    def __post_init__(self):
        if self.gmail is None:
            self.gmail = GmailConfig()
        if self.email is None:
            self.email = EmailConfig()
        if self.logging is None:
            self.logging = LoggingConfig()

# Global config instance
_config: Optional[Config] = None

def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config

def load_config() -> Config:
    """Load configuration from environment variables and files."""
    config = Config()
    
    # Load from environment variables
    config.debug = os.getenv("DEBUG", "false").lower() == "true"
    config.dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    
    # Gmail configuration
    config.gmail.credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH", config.gmail.credentials_path)
    config.gmail.token_path = os.getenv("GMAIL_TOKEN_PATH", config.gmail.token_path)
    config.gmail.max_results = int(os.getenv("GMAIL_MAX_RESULTS", config.gmail.max_results))
    
    # Email configuration
    config.email.auto_reply_enabled = os.getenv("AUTO_REPLY_ENABLED", "false").lower() == "true"
    config.email.reply_template = os.getenv("REPLY_TEMPLATE", config.email.reply_template)
    config.email.signature = os.getenv("EMAIL_SIGNATURE", config.email.signature)
    
    # Logging configuration
    config.logging.level = os.getenv("LOG_LEVEL", config.logging.level)
    config.logging.file_path = os.getenv("LOG_FILE_PATH", config.logging.file_path)
    
    # Try to load from config.json if it exists
    config_file = Path("config.json")
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
                # Update config with file data
                if 'gmail' in data:
                    for key, value in data['gmail'].items():
                        if hasattr(config.gmail, key):
                            setattr(config.gmail, key, value)
                if 'email' in data:
                    for key, value in data['email'].items():
                        if hasattr(config.email, key):
                            setattr(config.email, key, value)
                if 'logging' in data:
                    for key, value in data['logging'].items():
                        if hasattr(config.logging, key):
                            setattr(config.logging, key, value)
                if 'debug' in data:
                    config.debug = data['debug']
                if 'dry_run' in data:
                    config.dry_run = data['dry_run']
        except Exception as e:
            print(f"Warning: Could not load config.json: {e}")
    
    return config

def save_config(config: Config) -> None:
    """Save configuration to config.json file."""
    config_file = Path("config.json")
    try:
        with open(config_file, 'w') as f:
            json.dump(asdict(config), f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save config.json: {e}")

def set_config_path(path: str) -> None:
    """Set the configuration file path."""
    # This is a placeholder for compatibility
    pass

# Default reply template
DEFAULT_REPLY_TEMPLATE = """Hi {sender_name},

Thank you for your email regarding "{subject}".

I have received your message and will get back to you as soon as possible.

Best regards,
Fikiri Solutions Team"""

# Default signature
DEFAULT_SIGNATURE = """

---
Fikiri Solutions
Automated Response System"""
