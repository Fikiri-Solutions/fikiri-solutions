#!/usr/bin/env python3
"""
Fikiri Solutions - Environment Validation Script
Validates all required environment variables before deployment.
"""

import os
import sys
import json
from typing import Dict, List, Tuple, Optional
from pathlib import Path

class EnvironmentValidator:
    """Validates environment configuration for Fikiri Solutions."""
    
    def __init__(self):
        self.required_vars = {
            # Core API Keys
            'OPENAI_API_KEY': {
                'required': True,
                'description': 'OpenAI API key for AI Assistant functionality',
                'validation': self._validate_openai_key
            },
            
            # Email Service Credentials
            'GMAIL_CREDENTIALS': {
                'required': False,
                'description': 'Gmail OAuth credentials (JSON string)',
                'validation': self._validate_json_credentials
            },
            'OUTLOOK_ACCESS_TOKEN': {
                'required': False,
                'description': 'Microsoft Graph API access token',
                'validation': self._validate_token_format
            },
            'OUTLOOK_CLIENT_ID': {
                'required': False,
                'description': 'Microsoft Graph API client ID',
                'validation': self._validate_uuid_format
            },
            
            # Database Configuration
            'DATABASE_URL': {
                'required': False,
                'description': 'Database connection string',
                'validation': self._validate_database_url
            },
            
            # Security Configuration
            'SECRET_KEY': {
                'required': True,
                'description': 'Flask secret key for session management',
                'validation': self._validate_secret_key
            },
            'JWT_SECRET': {
                'required': False,
                'description': 'JWT signing secret',
                'validation': self._validate_secret_key
            },
            
            # External Service Configuration
            'STRIPE_SECRET_KEY': {
                'required': False,
                'description': 'Stripe secret key for billing',
                'validation': self._validate_stripe_key
            },
            'STRIPE_PUBLISHABLE_KEY': {
                'required': False,
                'description': 'Stripe publishable key',
                'validation': self._validate_stripe_key
            },
            
            # Monitoring & Logging
            'LOG_LEVEL': {
                'required': False,
                'description': 'Logging level (DEBUG, INFO, WARNING, ERROR)',
                'validation': self._validate_log_level,
                'default': 'INFO'
            },
            'SENTRY_DSN': {
                'required': False,
                'description': 'Sentry DSN for error tracking',
                'validation': self._validate_sentry_dsn
            },
            
            # Feature Flags
            'ENABLE_TENSORFLOW': {
                'required': False,
                'description': 'Enable TensorFlow features (true/false)',
                'validation': self._validate_boolean,
                'default': 'false'
            },
            'ENABLE_ANALYTICS': {
                'required': False,
                'description': 'Enable analytics tracking (true/false)',
                'validation': self._validate_boolean,
                'default': 'true'
            }
        }
        
        self.optional_vars = {
            'REDIS_URL': 'Redis connection for caching',
            'SMTP_HOST': 'SMTP server for email sending',
            'SMTP_PORT': 'SMTP server port',
            'SMTP_USERNAME': 'SMTP authentication username',
            'SMTP_PASSWORD': 'SMTP authentication password'
        }
    
    def validate_all(self) -> Tuple[bool, List[str]]:
        """Validate all environment variables."""
        errors = []
        warnings = []
        
        print("🔍 Validating Environment Configuration...")
        print("=" * 50)
        
        # Check required variables
        for var_name, config in self.required_vars.items():
            value = os.getenv(var_name)
            
            if not value:
                if config['required']:
                    error_msg = f"❌ REQUIRED: {var_name} - {config['description']}"
                    errors.append(error_msg)
                    print(error_msg)
                else:
                    default_value = config.get('default', 'Not set')
                    warning_msg = f"⚠️  OPTIONAL: {var_name} - {config['description']} (default: {default_value})"
                    warnings.append(warning_msg)
                    print(warning_msg)
            else:
                # Validate the value if validation function exists
                if 'validation' in config:
                    try:
                        is_valid, validation_msg = config['validation'](value)
                        if is_valid:
                            print(f"✅ {var_name}: {validation_msg}")
                        else:
                            error_msg = f"❌ {var_name}: {validation_msg}"
                            errors.append(error_msg)
                            print(error_msg)
                    except Exception as e:
                        error_msg = f"❌ {var_name}: Validation error - {str(e)}"
                        errors.append(error_msg)
                        print(error_msg)
                else:
                    print(f"✅ {var_name}: Set")
        
        # Check optional variables
        print("\n📋 Optional Variables:")
        for var_name, description in self.optional_vars.items():
            value = os.getenv(var_name)
            if value:
                print(f"✅ {var_name}: Set")
            else:
                print(f"⚪ {var_name}: Not set - {description}")
        
        # Summary
        print("\n" + "=" * 50)
        if errors:
            print(f"❌ VALIDATION FAILED: {len(errors)} errors found")
            return False, errors
        else:
            print(f"✅ VALIDATION PASSED: {len(warnings)} warnings")
            if warnings:
                print("\n⚠️  Warnings:")
                for warning in warnings:
                    print(f"   {warning}")
            return True, warnings
    
    def _validate_openai_key(self, value: str) -> Tuple[bool, str]:
        """Validate OpenAI API key format."""
        if not value.startswith('sk-'):
            return False, "OpenAI API key must start with 'sk-'"
        if len(value) < 20:
            return False, "OpenAI API key appears too short"
        return True, "Valid OpenAI API key format"
    
    def _validate_json_credentials(self, value: str) -> Tuple[bool, str]:
        """Validate JSON credentials format."""
        try:
            json.loads(value)
            return True, "Valid JSON format"
        except json.JSONDecodeError:
            return False, "Invalid JSON format"
    
    def _validate_token_format(self, value: str) -> Tuple[bool, str]:
        """Validate token format."""
        if len(value) < 10:
            return False, "Token appears too short"
        return True, "Valid token format"
    
    def _validate_uuid_format(self, value: str) -> Tuple[bool, str]:
        """Validate UUID format."""
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, value, re.IGNORECASE):
            return False, "Invalid UUID format"
        return True, "Valid UUID format"
    
    def _validate_database_url(self, value: str) -> Tuple[bool, str]:
        """Validate database URL format."""
        if not value.startswith(('postgresql://', 'mysql://', 'sqlite:///')):
            return False, "Invalid database URL format"
        return True, "Valid database URL format"
    
    def _validate_secret_key(self, value: str) -> Tuple[bool, str]:
        """Validate secret key strength."""
        if len(value) < 32:
            return False, "Secret key should be at least 32 characters"
        return True, "Strong secret key"
    
    def _validate_stripe_key(self, value: str) -> Tuple[bool, str]:
        """Validate Stripe key format."""
        if value.startswith('sk_') or value.startswith('pk_'):
            return True, "Valid Stripe key format"
        return False, "Stripe key must start with 'sk_' or 'pk_'"
    
    def _validate_log_level(self, value: str) -> Tuple[bool, str]:
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if value.upper() in valid_levels:
            return True, f"Valid log level: {value.upper()}"
        return False, f"Invalid log level. Must be one of: {', '.join(valid_levels)}"
    
    def _validate_sentry_dsn(self, value: str) -> Tuple[bool, str]:
        """Validate Sentry DSN format."""
        if value.startswith('https://'):
            return True, "Valid Sentry DSN format"
        return False, "Sentry DSN must start with 'https://'"
    
    def _validate_boolean(self, value: str) -> Tuple[bool, str]:
        """Validate boolean value."""
        if value.lower() in ['true', 'false', '1', '0', 'yes', 'no']:
            return True, f"Valid boolean: {value.lower()}"
        return False, "Must be a boolean value (true/false, 1/0, yes/no)"
    
    def generate_env_template(self) -> str:
        """Generate a .env.template file."""
        template_lines = [
            "# Fikiri Solutions - Environment Configuration",
            "# Copy this file to .env and fill in your values",
            "",
            "# Core API Keys",
            "OPENAI_API_KEY=sk-your-openai-key-here",
            "",
            "# Email Service Credentials (Optional)",
            "GMAIL_CREDENTIALS={\"type\":\"service_account\",\"project_id\":\"your-project\"}",
            "OUTLOOK_ACCESS_TOKEN=your-outlook-token-here",
            "OUTLOOK_CLIENT_ID=your-client-id-here",
            "",
            "# Security",
            "SECRET_KEY=your-super-secret-key-here-minimum-32-chars",
            "",
            "# Optional Services",
            "STRIPE_SECRET_KEY=sk_test_your-stripe-key",
            "STRIPE_PUBLISHABLE_KEY=pk_test_your-stripe-key",
            "",
            "# Monitoring",
            "LOG_LEVEL=INFO",
            "SENTRY_DSN=https://your-sentry-dsn@sentry.io/project",
            "",
            "# Feature Flags",
            "ENABLE_TENSORFLOW=false",
            "ENABLE_ANALYTICS=true"
        ]
        
        return "\n".join(template_lines)

def main():
    """Main validation function."""
    validator = EnvironmentValidator()
    
    # Check if we're generating template
    if len(sys.argv) > 1 and sys.argv[1] == '--generate-template':
        template = validator.generate_env_template()
        with open('.env.template', 'w') as f:
            f.write(template)
        print("✅ Generated .env.template file")
        return
    
    # Run validation
    is_valid, messages = validator.validate_all()
    
    if not is_valid:
        print("\n🚨 DEPLOYMENT BLOCKED: Environment validation failed!")
        print("Fix the errors above before deploying.")
        sys.exit(1)
    else:
        print("\n🚀 Environment validation passed! Ready for deployment.")
        sys.exit(0)

if __name__ == "__main__":
    main()
