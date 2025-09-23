#!/bin/bash
# Fikiri Solutions - Redis Environment Setup
# This script sets up the correct Redis Cloud environment variables

echo "🔧 Setting up Redis Cloud environment variables..."

# Export Redis Cloud configuration
export REDIS_URL="redis://default:fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H@redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com:19575"
export REDIS_HOST="redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com"
export REDIS_PORT="19575"
export REDIS_PASSWORD="fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H"
export REDIS_DB="0"

echo "✅ Redis environment variables set:"
echo "   REDIS_HOST: $REDIS_HOST"
echo "   REDIS_PORT: $REDIS_PORT"
echo "   REDIS_DB: $REDIS_DB"
echo "   REDIS_URL: [HIDDEN]"

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
"

echo "🚀 You can now run the app with: source venv_local/bin/activate && python app.py"
