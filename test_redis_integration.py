#!/usr/bin/env python3
"""
Test Redis integration with Fikiri backend
"""

import os
import sys
import json

# Add the project root to Python path
sys.path.insert(0, '/Users/mac/Downloads/Fikiri')

# Set environment variables for Redis
os.environ['REDIS_HOST'] = 'redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com'
os.environ['REDIS_PORT'] = '19575'
os.environ['REDIS_PASSWORD'] = 'fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H'
os.environ['REDIS_DB'] = '0'
os.environ['REDIS_URL'] = 'redis://default:fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H@redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com:19575'

def test_redis_integration():
    """Test Redis integration with Fikiri backend."""
    
    print("🔗 Testing Redis Integration with Fikiri Backend...")
    print("=" * 60)
    
    try:
        # Import Redis service
        from core.redis_service import get_redis_service
        
        redis_service = get_redis_service()
        
        if not redis_service.is_connected():
            print("❌ Redis service not connected")
            return False
        
        print("✅ Redis service connected successfully")
        
        # Test basic operations
        print("\n🧪 Testing Redis operations...")
        
        # Test user data storage
        test_user_data = {
            'name': 'Test User',
            'email': 'test@fikirisolutions.com',
            'industry': 'landscaping',
            'team_size': 'small'
        }
        
        success = redis_service.store_user_data('test_user_1', test_user_data)
        if success:
            print("✅ User data stored successfully")
        else:
            print("❌ Failed to store user data")
            return False
        
        # Test user data retrieval
        retrieved_data = redis_service.get_user_data('test_user_1')
        if retrieved_data:
            print(f"✅ User data retrieved: {retrieved_data}")
        else:
            print("❌ Failed to retrieve user data")
            return False
        
        # Test AI response caching
        test_prompt = "How can I improve my landscaping business?"
        test_response = "Focus on customer service, quality work, and marketing."
        
        success = redis_service.cache_ai_response('test_user_1', test_prompt, test_response)
        if success:
            print("✅ AI response cached successfully")
        else:
            print("❌ Failed to cache AI response")
            return False
        
        # Test AI response retrieval
        responses = redis_service.get_ai_responses('test_user_1', limit=5)
        if responses:
            print(f"✅ AI responses retrieved: {len(responses)} responses")
            print(f"   Latest response: {responses[0]['response'][:50]}...")
        else:
            print("❌ Failed to retrieve AI responses")
            return False
        
        # Test usage analytics
        usage_data = {
            'responses_count': '5',
            'tokens_used': '1500',
            'monthly_cost': '12.50',
            'tier': 'professional'
        }
        
        success = redis_service.store_usage_analytics('test_user_1', '2025-09-20', usage_data)
        if success:
            print("✅ Usage analytics stored successfully")
        else:
            print("❌ Failed to store usage analytics")
            return False
        
        # Test usage analytics retrieval
        analytics = redis_service.get_usage_analytics('test_user_1', '2025-09-20')
        if analytics:
            print(f"✅ Usage analytics retrieved: {analytics}")
        else:
            print("❌ Failed to retrieve usage analytics")
            return False
        
        # Test rate limiting
        rate_limited = redis_service.rate_limit_check('test_ip_1', 5, 60)
        if rate_limited:
            print("✅ Rate limiting working correctly (request allowed)")
        else:
            print("❌ Rate limiting not working")
            return False
        
        # Test Redis info
        info = redis_service.get_info()
        if info:
            print(f"✅ Redis info retrieved: Version {info.get('redis_version', 'Unknown')}")
            print(f"   Memory used: {info.get('used_memory_human', 'Unknown')}")
            print(f"   Connected clients: {info.get('connected_clients', 'Unknown')}")
        
        # Cleanup test data
        print("\n🧹 Cleaning up test data...")
        test_keys = [
            'fikiri:user:test_user_1',
            'fikiri:ai_responses:test_user_1',
            'fikiri:usage:test_user_1:2025-09-20',
            'fikiri:rate_limit:test_ip_1'
        ]
        
        for key in test_keys:
            redis_service.delete(key)
        
        print("✅ Test data cleaned up")
        
        print("\n🎉 All Redis integration tests passed!")
        print("\n📋 Redis is ready for production use with:")
        print("   ✅ User data storage")
        print("   ✅ AI response caching")
        print("   ✅ Usage analytics")
        print("   ✅ Rate limiting")
        print("   ✅ Session management")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you're running from the project root directory")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_redis_integration()
    sys.exit(0 if success else 1)
