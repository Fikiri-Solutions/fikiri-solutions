#!/usr/bin/env python3
"""
Fikiri Solutions - Runtime Configuration (Canonical)
Lightweight configuration management without heavy dependencies.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class MinimalConfig:
    """Minimal configuration class - no dataclasses, no heavy imports."""

    def __init__(self):
        self.gmail_credentials_path = "auth/credentials.json"
        self.gmail_token_path = "auth/token.pkl"
        self.gmail_scopes = ["https://www.googleapis.com/auth/gmail.modify"]
        self.gmail_user_id = "me"
        self.gmail_max_results = 10

        self.auto_reply_enabled = False
        self.reply_template = ""
        self.signature = ""

        self.log_level = "INFO"
        self.log_file = None

        self.debug = False
        self.dry_run = False

        self.redis_host = "localhost"
        self.redis_port = 6379
        self.redis_password = None
        self.redis_db = 0
        self.redis_url = None
        self.redis_max_connections = 10

        self._load_from_env()
        self._load_from_file()

    def _load_from_env(self):
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
        self.gmail_credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH", self.gmail_credentials_path)
        self.gmail_token_path = os.getenv("GMAIL_TOKEN_PATH", self.gmail_token_path)
        try:
            self.gmail_max_results = int(os.getenv("GMAIL_MAX_RESULTS", str(self.gmail_max_results)))
        except ValueError:
            logger.warning("Invalid GMAIL_MAX_RESULTS value, using default: %s", self.gmail_max_results)
        self.auto_reply_enabled = os.getenv("AUTO_REPLY_ENABLED", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)

        self.redis_host = os.getenv("REDIS_HOST", self.redis_host)
        self.redis_port = int(os.getenv("REDIS_PORT", str(self.redis_port)))
        self.redis_password = os.getenv("REDIS_PASSWORD")
        self.redis_db = int(os.getenv("REDIS_DB", str(self.redis_db)))
        self.redis_url = os.getenv("REDIS_URL")

    def _load_from_file(self):
        config_file = Path("config.json")
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        if hasattr(self, key):
                            setattr(self, key, value)
            except Exception as e:
                logger.warning("Could not load config.json: %s", e)

    def save(self):
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
            logger.info("Configuration saved to config.json")
        except Exception as e:
            logger.error("Could not save config.json: %s", e)

    def get_gmail_scopes(self):
        return self.gmail_scopes

    def is_debug(self):
        return self.debug

    def is_dry_run(self):
        return self.dry_run


_config: Optional[MinimalConfig] = None


def get_config() -> MinimalConfig:
    global _config
    if _config is None:
        _config = MinimalConfig()
    return _config


DEFAULT_REPLY_TEMPLATE = """Hi {sender_name},

Thank you for your email regarding "{subject}".

I have received your message and will get back to you as soon as possible.

Best regards,
Fikiri Solutions Team"""

DEFAULT_SIGNATURE = """

---
Fikiri Solutions
Automated Response System"""

