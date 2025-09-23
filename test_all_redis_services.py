#!/usr/bin/env python3
"""
Test all Redis services to ensure they connect to Redis Cloud
"""

import os
import sys

# Set Redis Cloud environment variables FIRST
os.environ['REDIS_URL'] = 'redis://default:fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H@redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com:19575'
os.environ['REDIS_HOST'] = 'redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com'
os.environ['REDIS_PORT'] = '19575'
os.environ['REDIS_PASSWORD'] = 'fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H'
os.environ['REDIS_DB'] = '0'

print("🔧 Redis Cloud environment variables set")
print(f"   REDIS_HOST: {os.environ.get('REDIS_HOST')}")
print(f"   REDIS_PORT: {os.environ.get('REDIS_PORT')}")
print()

def test_redis_service():
    """Test RedisService"""
    print("🔍 Testing RedisService...")
    try:
        from core.redis_service import redis_service
        if redis_service.is_connected():
            print("✅ RedisService connected to Redis Cloud")
            return True
        else:
            print("❌ RedisService not connected")
            return False
    except Exception as e:
        print(f"❌ RedisService test failed: {e}")
        return False

def test_redis_cache():
    """Test FikiriCache"""
    print("🔍 Testing FikiriCache...")
    try:
        from core.redis_cache import FikiriCache
        cache = FikiriCache()
        if cache.is_connected():
            print("✅ FikiriCache connected to Redis Cloud")
            return True
        else:
            print("❌ FikiriCache not connected")
            return False
    except Exception as e:
        print(f"❌ FikiriCache test failed: {e}")
        return False

def test_redis_sessions():
    """Test RedisSessionManager"""
    print("🔍 Testing RedisSessionManager...")
    try:
        from core.redis_sessions import session_manager
        if session_manager.is_connected():
            print("✅ RedisSessionManager connected to Redis Cloud")
            return True
        else:
            print("❌ RedisSessionManager not connected")
            return False
    except Exception as e:
        print(f"❌ RedisSessionManager test failed: {e}")
        return False

def test_redis_queues():
    """Test RedisQueue"""
    print("🔍 Testing RedisQueue...")
    try:
        from core.redis_queues import email_queue
        if email_queue.is_connected():
            print("✅ RedisQueue connected to Redis Cloud")
            return True
        else:
            print("❌ RedisQueue not connected")
            return False
    except Exception as e:
        print(f"❌ RedisQueue test failed: {e}")
        return False

def test_redis_rate_limiting():
    """Test RedisRateLimiter"""
    print("🔍 Testing RedisRateLimiter...")
    try:
        from core.redis_rate_limiting import rate_limiter
        if rate_limiter.is_connected():
            print("✅ RedisRateLimiter connected to Redis Cloud")
            return True
        else:
            print("❌ RedisRateLimiter not connected")
            return False
    except Exception as e:
        print(f"❌ RedisRateLimiter test failed: {e}")
        return False

def test_backend_cache():
    """Test CacheManager from backend_excellence"""
    print("🔍 Testing CacheManager...")
    try:
        from core.backend_excellence import CacheManager
        cache_manager = CacheManager()
        if cache_manager.enabled:
            print("✅ CacheManager connected to Redis Cloud")
            return True
        else:
            print("❌ CacheManager not connected")
            return False
    except Exception as e:
        print(f"❌ CacheManager test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing all Redis services...")
    print()
    
    results = []
    results.append(test_redis_service())
    results.append(test_redis_cache())
    results.append(test_redis_sessions())
    results.append(test_redis_queues())
    results.append(test_redis_rate_limiting())
    results.append(test_backend_cache())
    
    print()
    print("📊 Test Results:")
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All {total} Redis services connected successfully!")
        print("🎉 No more localhost:6379 connection errors!")
    else:
        print(f"❌ {total - passed} out of {total} Redis services failed to connect")
        print("🔧 Some services may still be using localhost:6379")
    
    sys.exit(0 if passed == total else 1)
