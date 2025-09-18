#!/usr/bin/env python3
"""
Environment Setup Script for Fikiri Solutions
Helps configure the development environment
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Check current environment configuration"""
    print("🔍 Checking Fikiri Environment Configuration...")
    print("=" * 50)
    
    # Check for required environment variables
    env_vars = {
        'OPENAI_API_KEY': 'OpenAI API Key (for AI features)',
        'REDIS_URL': 'Redis URL (for caching)',
        'FLASK_ENV': 'Flask Environment',
        'DATABASE_URL': 'Database URL'
    }
    
    missing_vars = []
    for var, description in env_vars.items():
        value = os.getenv(var)
        if value:
            if var == 'OPENAI_API_KEY':
                # Mask the API key for security
                masked_value = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
                print(f"✅ {var}: {masked_value}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Not set ({description})")
            missing_vars.append(var)
    
    print("\n" + "=" * 50)
    
    # Check Redis connection
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("✅ Redis: Connected successfully")
    except Exception as e:
        print(f"❌ Redis: Connection failed - {e}")
        print("   💡 Install Redis: brew install redis && brew services start redis")
    
    # Check for data files
    data_files = {
        'data/leads.json': 'Leads data file',
        'data/business_profile.json': 'Business profile',
        'data/faq_knowledge.json': 'FAQ knowledge base'
    }
    
    print("\n📁 Data Files:")
    for file_path, description in data_files.items():
        if Path(file_path).exists():
            print(f"✅ {file_path}: Found")
        else:
            print(f"❌ {file_path}: Missing ({description})")
    
    return missing_vars

def create_env_file():
    """Create a .env file with default values"""
    env_content = """# Fikiri Solutions Environment Configuration
# Copy this file to .env and update with your actual values

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True

# Database Configuration
DATABASE_URL=sqlite:///data/fikiri.db

# Security
SECRET_KEY=your_secret_key_here

# Email Configuration (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Monitoring
ENABLE_MONITORING=True
LOG_LEVEL=INFO
"""
    
    env_file = Path('.env')
    if env_file.exists():
        print("⚠️  .env file already exists. Skipping creation.")
        return
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print("✅ Created .env file with default configuration")
    print("📝 Please edit .env file with your actual values")

def install_redis():
    """Provide instructions for installing Redis"""
    print("\n🔧 Redis Installation Instructions:")
    print("=" * 40)
    print("1. Install Redis using Homebrew:")
    print("   brew install redis")
    print("\n2. Start Redis service:")
    print("   brew services start redis")
    print("\n3. Verify Redis is running:")
    print("   redis-cli ping")
    print("   (Should return 'PONG')")

def main():
    """Main setup function"""
    print("🚀 Fikiri Solutions Environment Setup")
    print("=" * 50)
    
    missing_vars = check_environment()
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        create_env_file()
    
    # Check if Redis is missing
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
    except:
        install_redis()
    
    print("\n🎯 Next Steps:")
    print("1. Install Redis if not already installed")
    print("2. Set your OpenAI API key in .env file")
    print("3. Run: python app.py")
    print("\n✨ Happy coding!")

if __name__ == "__main__":
    main()
