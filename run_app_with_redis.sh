#!/bin/bash
# Fikiri Solutions - Run App with Redis Cloud
# This script sets up Redis Cloud environment and runs the app

cd "$(dirname "$0")"

echo "🚀 Starting Fikiri Solutions with Redis Cloud..."

# Set Redis Cloud environment variables BEFORE activating venv
export REDIS_URL="redis://default:fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H@redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com:19575"
export REDIS_HOST="redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com"
export REDIS_PORT="19575"
export REDIS_PASSWORD="fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H"
export REDIS_DB="0"

echo "✅ Redis Cloud environment variables set"

# Activate virtual environment
source venv_local/bin/activate

# Check if virtual environment is active
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment activated: $VIRTUAL_ENV"
else
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

# Test Redis connection
echo "🔍 Testing Redis connection..."
python -c "
import redis
import os
try:
    client = redis.from_url(os.getenv('REDIS_URL'), decode_responses=True)
    client.ping()
    print('✅ Redis connection successful!')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    exit(1)
"

# Run the application
echo "🚀 Starting Fikiri Solutions application..."
python app.py
