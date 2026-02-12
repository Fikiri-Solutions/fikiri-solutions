#!/usr/bin/env python3
"""
Fikiri Solutions - Secret Generation Script
Generates new secrets for rotation after potential exposure.
"""

import secrets
import base64
import os
from datetime import datetime

def generate_jwt_secret():
    """Generate a secure JWT secret key (32+ bytes)"""
    return secrets.token_urlsafe(32)

def generate_flask_secret():
    """Generate a secure Flask secret key (32+ bytes)"""
    return secrets.token_urlsafe(32)

def generate_fernet_key():
    """Generate a new Fernet encryption key (32 bytes base64 encoded)"""
    # Fernet requires 32 bytes, base64 encoded
    key = secrets.token_bytes(32)
    return base64.urlsafe_b64encode(key).decode('utf-8')

def generate_random_token(length=32):
    """Generate a random token"""
    return secrets.token_urlsafe(length)

def main():
    """Generate all new secrets"""
    print("=" * 60)
    print("🔐 Fikiri Solutions - Secret Generation")
    print("=" * 60)
    print()
    print("⚠️  WARNING: These are NEW secrets. Save them securely!")
    print("⚠️  Update your .env file and Render environment variables.")
    print()
    print("-" * 60)
    
    secrets_dict = {
        'JWT_SECRET_KEY': generate_jwt_secret(),
        'FLASK_SECRET_KEY': generate_flask_secret(),
        'FERNET_KEY': generate_fernet_key(),
        'MAINTENANCE_TOKEN': generate_random_token(32),
    }
    
    # Generate output
    output_lines = [
        "# Fikiri Solutions - NEW SECRETS",
        f"# Generated: {datetime.now().isoformat()}",
        "# ",
        "# ⚠️  CRITICAL: Update these in:",
        "#   1. Local .env file",
        "#   2. Render environment variables",
        "#   3. Any other deployment environments",
        "# ",
        "# After updating, test thoroughly before deploying!",
        "# ",
        ""
    ]
    
    for key, value in secrets_dict.items():
        output_lines.append(f"{key}={value}")
    
    output_lines.extend([
        "",
        "# ",
        "# Third-party services that need manual rotation:",
        "# ",
        "# 1. Upstash Redis:",
        "#    - Go to Upstash Console → Your Database → Settings",
        "#    - Click 'Reset Credentials'",
        "#    - Update REDIS_URL, UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN",
        "# ",
        "# 2. Google OAuth:",
        "#    - Go to Google Cloud Console → APIs & Services → Credentials",
        "#    - Create new OAuth 2.0 Client ID",
        "#    - Update GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET",
        "# ",
        "# 3. OpenAI:",
        "#    - Go to OpenAI Platform → API Keys",
        "#    - Create new secret key",
        "#    - Revoke old key",
        "#    - Update OPENAI_API_KEY",
        "# ",
        "# 4. Stripe (if used):",
        "#    - Go to Stripe Dashboard → Developers → API keys",
        "#    - Create new secret key",
        "#    - Update STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET",
        "# ",
    ])
    
    output = "\n".join(output_lines)
    
    # Print to console
    print(output)
    print()
    print("-" * 60)
    
    # Save to file
    output_file = "NEW_SECRETS.txt"
    with open(output_file, 'w') as f:
        f.write(output)
    
    print(f"✅ Secrets saved to: {output_file}")
    print()
    print("⚠️  SECURITY REMINDERS:")
    print("   1. Do NOT commit NEW_SECRETS.txt to Git")
    print("   2. Delete NEW_SECRETS.txt after updating environments")
    print("   3. Verify .env is in .gitignore")
    print("   4. Test locally before deploying")
    print()
    print("=" * 60)

if __name__ == "__main__":
    main()

