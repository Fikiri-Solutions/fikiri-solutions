#!/usr/bin/env python3
"""
Redis Connection Test Script for Fikiri Solutions
Tests connection to Redis Cloud database
"""

import os
import sys
import redis
import json
import time
from datetime import datetime

def test_redis_connection():
    """Test Redis Cloud connection and basic operations"""
    
    print("🔗 Testing Redis Cloud Connection...")
    print("=" * 50)
    
    # Redis configuration
    redis_config = {
        'host': 'redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com',
        'port': 19575,
        'password': 'fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H',
        'db': 0,
        'decode_responses': True,
        'socket_connect_timeout': 5,
        'socket_timeout': 5,
        'retry_on_timeout': True
    }
    
    try:
        # Connect to Redis
        print("📡 Connecting to Redis Cloud...")
        r = redis.Redis(**redis_config)
        
        # Test basic connection
        print("🔍 Testing basic connection...")
        ping_result = r.ping()
        print(f"✅ Ping successful: {ping_result}")
        
        # Test basic operations
        print("\n🧪 Testing basic operations...")
        
        # String operations
        r.set('fikiri:test:string', 'Hello Redis Cloud!')
        value = r.get('fikiri:test:string')
        print(f"✅ String set/get: {value}")
        
        # Hash operations
        user_data = {
            'name': 'Fikiri Test User',
            'email': 'test@fikirisolutions.com',
            'created_at': datetime.now().isoformat()
        }
        r.hset('fikiri:test:user:1', mapping=user_data)
        retrieved_data = r.hgetall('fikiri:test:user:1')
        print(f"✅ Hash operations: {retrieved_data}")
        
        # List operations
        r.lpush('fikiri:test:leads', 'lead1', 'lead2', 'lead3')
        leads = r.lrange('fikiri:test:leads', 0, -1)
        print(f"✅ List operations: {leads}")
        
        # Set operations
        r.sadd('fikiri:test:industries', 'landscaping', 'construction', 'real-estate')
        industries = r.smembers('fikiri:test:industries')
        print(f"✅ Set operations: {industries}")
        
        # JSON operations (Redis Stack feature)
        try:
            json_data = {
                'user_id': 1,
                'name': 'Test User',
                'preferences': {
                    'theme': 'dark',
                    'notifications': True
                }
            }
            r.json().set('fikiri:test:json:1', '$', json_data)
            retrieved_json = r.json().get('fikiri:test:json:1')
            print(f"✅ JSON operations: {retrieved_json}")
        except Exception as e:
            print(f"⚠️  JSON operations not available: {e}")
        
        # Test expiration
        r.setex('fikiri:test:expire', 5, 'This will expire')
        ttl = r.ttl('fikiri:test:expire')
        print(f"✅ Expiration test: TTL = {ttl} seconds")
        
        # Test Redis info
        print("\n📊 Redis Server Information:")
        info = r.info()
        print(f"   Redis Version: {info.get('redis_version', 'Unknown')}")
        print(f"   Used Memory: {info.get('used_memory_human', 'Unknown')}")
        print(f"   Connected Clients: {info.get('connected_clients', 'Unknown')}")
        print(f"   Total Commands Processed: {info.get('total_commands_processed', 'Unknown')}")
        
        # Cleanup test data
        print("\n🧹 Cleaning up test data...")
        test_keys = r.keys('fikiri:test:*')
        if test_keys:
            r.delete(*test_keys)
            print(f"✅ Cleaned up {len(test_keys)} test keys")
        
        print("\n🎉 All Redis tests passed successfully!")
        return True
        
    except redis.ConnectionError as e:
        print(f"❌ Connection failed: {e}")
        return False
    except redis.AuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        return False
    except redis.TimeoutError as e:
        print(f"❌ Timeout error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_redis_performance():
    """Test Redis performance with bulk operations"""
    
    print("\n⚡ Testing Redis Performance...")
    print("=" * 50)
    
    redis_config = {
        'host': 'redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com',
        'port': 19575,
        'password': 'fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H',
        'db': 0,
        'decode_responses': True
    }
    
    try:
        r = redis.Redis(**redis_config)
        
        # Test bulk operations
        start_time = time.time()
        
        # Bulk set operations
        pipe = r.pipeline()
        for i in range(100):
            pipe.set(f'fikiri:perf:test:{i}', f'value_{i}')
        pipe.execute()
        
        set_time = time.time() - start_time
        print(f"✅ Bulk set (100 keys): {set_time:.3f} seconds")
        
        # Bulk get operations
        start_time = time.time()
        pipe = r.pipeline()
        for i in range(100):
            pipe.get(f'fikiri:perf:test:{i}')
        results = pipe.execute()
        
        get_time = time.time() - start_time
        print(f"✅ Bulk get (100 keys): {get_time:.3f} seconds")
        
        # Cleanup
        test_keys = r.keys('fikiri:perf:test:*')
        if test_keys:
            r.delete(*test_keys)
            print(f"✅ Cleaned up {len(test_keys)} performance test keys")
        
        print(f"✅ Performance test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

def main():
    """Main test function"""
    
    print("🚀 Fikiri Solutions - Redis Cloud Connection Test")
    print("=" * 60)
    
    # Test basic connection
    basic_test = test_redis_connection()
    
    if basic_test:
        # Test performance
        perf_test = test_redis_performance()
        
        if perf_test:
            print("\n🎉 All tests passed! Redis Cloud is ready for production.")
            print("\n📋 Next Steps:")
            print("   1. Update your .env file with Redis credentials")
            print("   2. Install redis package: pip install redis>=4.0.0")
            print("   3. Update your backend configuration")
            print("   4. Deploy to production")
            sys.exit(0)
        else:
            print("\n⚠️  Performance test failed. Check Redis configuration.")
            sys.exit(1)
    else:
        print("\n❌ Basic connection test failed. Check Redis credentials.")
        sys.exit(1)

if __name__ == "__main__":
    main()
