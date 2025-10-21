"""
Configuration management for Fikiri Solutions
Environment-aware settings for OAuth and other integrations
"""

import os
from typing import Optional

# Environment detection
ENV = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENV == "production"

class Config:
    """Centralized configuration management"""
    
    # OAuth Configuration
    OAUTH_REDIRECT_URL = (
        os.getenv("OAUTH_REDIRECT_URL_PROD") if IS_PRODUCTION 
        else os.getenv("OAUTH_REDIRECT_URL_DEV", "http://localhost:3000/api/oauth/gmail/callback")
    )
    
    # JWT Configuration
    JWT_ACCESS_EXPIRY = int(os.getenv("JWT_ACCESS_EXPIRY", 30 * 60))  # 30 minutes
    JWT_REFRESH_EXPIRY = int(os.getenv("JWT_REFRESH_EXPIRY", 7 * 24 * 60 * 60))  # 7 days
    
    # Database Configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/fikiri.db")
    
    # Redis Configuration
    REDIS_URL = os.getenv("REDIS_URL")
    
    # API Configuration
    API_BASE_URL = (
        "https://fikirisolutions.com" if IS_PRODUCTION
        else "http://localhost:5000"
    )
    
    # Frontend Configuration
    FRONTEND_URL = (
        "https://fikirisolutions.com" if IS_PRODUCTION
        else "http://localhost:5173"
    )
    
    # CORS Configuration
    CORS_ORIGINS = [
        "https://fikirisolutions.com",
        "https://www.fikirisolutions.com",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ]
    
    # Security Configuration
    SESSION_COOKIE_DOMAIN = (
        ".fikirisolutions.com" if IS_PRODUCTION
        else None
    )
    
    # Monitoring Configuration
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    SENTRY_ENVIRONMENT = ENV
    
    @classmethod
    def get_oauth_redirect_url(cls) -> str:
        """Get the appropriate OAuth redirect URL based on environment"""
        return cls.OAUTH_REDIRECT_URL
    
    @classmethod
    def get_api_base_url(cls) -> str:
        """Get the appropriate API base URL based on environment"""
        return cls.API_BASE_URL
    
    @classmethod
    def get_frontend_url(cls) -> str:
        """Get the appropriate frontend URL based on environment"""
        return cls.FRONTEND_URL
    
    @classmethod
    def is_development(cls) -> bool:
        """Check if running in development mode"""
        return not IS_PRODUCTION
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production mode"""
        return IS_PRODUCTION

# Global config instance
config = Config()
