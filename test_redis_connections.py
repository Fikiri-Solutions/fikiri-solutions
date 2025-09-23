#!/usr/bin/env python3
"""
Test Redis connections for all services
"""

import os
import sys

# Set Redis environment variables
os.environ['REDIS_URL'] = 'redis://default:fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H@redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com:19575'
os.environ['REDIS_HOST'] = 'redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com'
os.environ['REDIS_PORT'] = '19575'
os.environ['REDIS_PASSWORD'] = 'fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H'
os.environ['REDIS_DB'] = '0'

print("🔧 Redis environment variables set:")
print(f"   REDIS_HOST: {os.environ.get('REDIS_HOST')}")
print(f"   REDIS_PORT: {os.environ.get('REDIS_PORT')}")
print(f"   REDIS_DB: {os.environ.get('REDIS_DB')}")
print(f"   REDIS_URL: [HIDDEN]")
print()

# Test Redis connection directly
print("🔍 Testing direct Redis connection...")
try:
    import redis
    client = redis.from_url(os.environ['REDIS_URL'], decode_responses=True)
    client.ping()
    print("✅ Direct Redis connection successful!")
except Exception as e:
    print(f"❌ Direct Redis connection failed: {e}")
    sys.exit(1)

# Test configuration loading
print("\n🔍 Testing configuration loading...")
try:
    from core.minimal_config import get_config
    config = get_config()
    print(f"✅ Config loaded - Redis host: {config.redis_host}")
    print(f"   Redis port: {config.redis_port}")
    print(f"   Redis URL: {config.redis_url[:50]}..." if config.redis_url else "   Redis URL: None")
except Exception as e:
    print(f"❌ Configuration loading failed: {e}")

# Test Redis services
print("\n🔍 Testing Redis services...")

try:
    from core.redis_service import redis_service
    if redis_service.is_connected():
        print("✅ Redis service connected")
    else:
        print("❌ Redis service not connected")
except Exception as e:
    print(f"❌ Redis service test failed: {e}")

try:
    from core.redis_cache import FikiriCache
    cache = FikiriCache()
    if cache.is_connected():
        print("✅ Redis cache connected")
    else:
        print("❌ Redis cache not connected")
except Exception as e:
    print(f"❌ Redis cache test failed: {e}")

try:
    from core.redis_sessions import session_manager
    if session_manager.is_connected():
        print("✅ Redis sessions connected")
    else:
        print("❌ Redis sessions not connected")
except Exception as e:
    print(f"❌ Redis sessions test failed: {e}")

try:
    from core.redis_rate_limiting import rate_limiter
    if rate_limiter.is_connected():
        print("✅ Redis rate limiter connected")
    else:
        print("❌ Redis rate limiter not connected")
except Exception as e:
    print(f"❌ Redis rate limiter test failed: {e}")

try:
    from core.redis_queues import email_queue
    if email_queue.is_connected():
        print("✅ Redis email queue connected")
    else:
        print("❌ Redis email queue not connected")
except Exception as e:
    print(f"❌ Redis email queue test failed: {e}")

print("\n🎉 Redis connection tests completed!")
