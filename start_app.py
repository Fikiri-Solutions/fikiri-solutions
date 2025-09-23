#!/usr/bin/env python3
"""
Fikiri Solutions - Application Startup Script
Sets up environment variables before importing modules
"""

import os
import sys

# Set Redis Cloud environment variables BEFORE any imports
os.environ['REDIS_URL'] = 'redis://default:fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H@redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com:19575'
os.environ['REDIS_HOST'] = 'redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com'
os.environ['REDIS_PORT'] = '19575'
os.environ['REDIS_PASSWORD'] = 'fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H'
os.environ['REDIS_DB'] = '0'

# Set other environment variables
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = 'False'

print("🔧 Environment variables configured:")
print(f"   REDIS_HOST: {os.environ.get('REDIS_HOST')}")
print(f"   REDIS_PORT: {os.environ.get('REDIS_PORT')}")
print(f"   FLASK_ENV: {os.environ.get('FLASK_ENV')}")
print()

# Now import and run the app
if __name__ == '__main__':
    print("🚀 Starting Fikiri Solutions...")
    
    # Import app after environment is set
    from app import app
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=8081,
        debug=False
    )
