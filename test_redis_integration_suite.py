#!/usr/bin/env python3
"""
Redis Integration Test Suite for Fikiri Solutions
Comprehensive testing of cache, sessions, rate limiting, and queues
"""

import os
import sys
import time
import json
import uuid
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, '/Users/mac/Downloads/Fikiri')

# Set environment variables for Redis
os.environ['REDIS_HOST'] = 'redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com'
os.environ['REDIS_PORT'] = '19575'
os.environ['REDIS_PASSWORD'] = 'fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H'
os.environ['REDIS_DB'] = '0'
os.environ['REDIS_URL'] = 'redis://default:fz0wvU6lk68C67y2bMwSrjGC38g3Dh6H@redis-19575.c17.us-east-1-4.ec2.redns.redis-cloud.com:19575'

def test_redis_cache():
    """Test Redis cache layer"""
    print("🧪 Testing Redis Cache Layer...")
    print("=" * 50)
    
    try:
        from core.redis_cache import get_cache
        
        cache = get_cache()
        
        if not cache.is_connected():
            print("❌ Cache not connected")
            return False
        
        print("✅ Cache connected successfully")
        
        # Test AI response caching
        test_prompt = "How can I improve my landscaping business?"
        test_response = "Focus on customer service, quality work, and marketing."
        test_user_id = "test_user_123"
        
        success = cache.cache_ai_response(test_prompt, test_response, test_user_id)
        if success:
            print("✅ AI response cached successfully")
        else:
            print("❌ AI response caching failed")
            return False
        
        # Test AI response retrieval
        cached_response = cache.get_cached_ai_response(test_prompt, test_user_id)
        if cached_response == test_response:
            print("✅ AI response retrieved from cache")
        else:
            print("❌ AI response retrieval failed")
            return False
        
        # Test email parsing cache
        test_email = "Subject: New Lead\nFrom: john@example.com\nBody: Interested in landscaping services"
        test_parsed = {
            "subject": "New Lead",
            "from": "john@example.com",
            "body": "Interested in landscaping services",
            "lead_score": 0.85
        }
        
        success = cache.cache_email_parse(test_email, test_parsed)
        if success:
            print("✅ Email parse cached successfully")
        else:
            print("❌ Email parse caching failed")
            return False
        
        # Test email parse retrieval
        cached_parse = cache.get_cached_email_parse(test_email)
        if cached_parse == test_parsed:
            print("✅ Email parse retrieved from cache")
        else:
            print("❌ Email parse retrieval failed")
            return False
        
        # Test lead scoring cache
        test_lead = {
            "email": "jane@example.com",
            "company": "ABC Landscaping",
            "industry": "landscaping"
        }
        test_score = 0.92
        
        success = cache.cache_lead_score(test_lead, test_score)
        if success:
            print("✅ Lead score cached successfully")
        else:
            print("❌ Lead score caching failed")
            return False
        
        # Test lead score retrieval
        cached_score = cache.get_cached_lead_score(test_lead)
        if cached_score == test_score:
            print("✅ Lead score retrieved from cache")
        else:
            print("❌ Lead score retrieval failed")
            return False
        
        # Test cache statistics
        stats = cache.get_cache_stats()
        if stats:
            print(f"✅ Cache stats retrieved: {stats}")
        else:
            print("❌ Cache stats failed")
            return False
        
        # Cleanup test data
        cache.clear_cache()
        print("✅ Cache test data cleaned up")
        
        print("🎉 Redis Cache Layer tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        return False

def test_redis_sessions():
    """Test Redis session management"""
    print("\n🧪 Testing Redis Session Management...")
    print("=" * 50)
    
    try:
        from core.redis_sessions import get_session_manager
        
        session_manager = get_session_manager()
        
        if not session_manager.is_connected():
            print("❌ Session manager not connected")
            return False
        
        print("✅ Session manager connected successfully")
        
        # Test session creation
        test_user_id = "test_user_456"
        test_user_data = {
            "name": "Test User",
            "email": "test@fikirisolutions.com",
            "industry": "landscaping",
            "role": "admin"
        }
        
        session_id = session_manager.create_session(test_user_id, test_user_data)
        if session_id:
            print(f"✅ Session created: {session_id}")
        else:
            print("❌ Session creation failed")
            return False
        
        # Test session retrieval
        session_data = session_manager.get_session(session_id)
        if session_data and session_data.get('user_id') == test_user_id:
            print("✅ Session retrieved successfully")
        else:
            print("❌ Session retrieval failed")
            return False
        
        # Test session update
        updates = {"last_login": datetime.now().isoformat()}
        success = session_manager.update_session(session_id, updates)
        if success:
            print("✅ Session updated successfully")
        else:
            print("❌ Session update failed")
            return False
        
        # Test session extension
        success = session_manager.extend_session(session_id, 3600)
        if success:
            print("✅ Session extended successfully")
        else:
            print("❌ Session extension failed")
            return False
        
        # Test user sessions
        user_sessions = session_manager.get_user_sessions(test_user_id)
        if len(user_sessions) > 0:
            print(f"✅ Found {len(user_sessions)} sessions for user")
        else:
            print("❌ User sessions retrieval failed")
            return False
        
        # Test session statistics
        stats = session_manager.get_session_stats()
        if stats:
            print(f"✅ Session stats: {stats}")
        else:
            print("❌ Session stats failed")
            return False
        
        # Test session deletion
        success = session_manager.delete_session(session_id)
        if success:
            print("✅ Session deleted successfully")
        else:
            print("❌ Session deletion failed")
            return False
        
        print("🎉 Redis Session Management tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Session test failed: {e}")
        return False

def test_redis_rate_limiting():
    """Test Redis rate limiting"""
    print("\n🧪 Testing Redis Rate Limiting...")
    print("=" * 50)
    
    try:
        from core.redis_rate_limiting import get_rate_limiter
        
        rate_limiter = get_rate_limiter()
        
        if not rate_limiter.is_connected():
            print("❌ Rate limiter not connected")
            return False
        
        print("✅ Rate limiter connected successfully")
        
        # Test rate limiting
        test_identifier = "test_user_789"
        limit = 5
        window = 60
        
        # Test multiple requests
        for i in range(7):  # Exceed the limit
            result = rate_limiter.check_rate_limit(test_identifier, limit, window)
            
            if i < limit:
                if result['allowed']:
                    print(f"✅ Request {i+1}: Allowed ({result['remaining']} remaining)")
                else:
                    print(f"❌ Request {i+1}: Should be allowed but was denied")
                    return False
            else:
                if not result['allowed']:
                    print(f"✅ Request {i+1}: Correctly denied (rate limit exceeded)")
                else:
                    print(f"❌ Request {i+1}: Should be denied but was allowed")
                    return False
        
        # Test rate limit status
        status = rate_limiter.get_rate_limit_status(test_identifier)
        if status:
            print(f"✅ Rate limit status: {status}")
        else:
            print("❌ Rate limit status failed")
            return False
        
        # Test rate limit reset
        success = rate_limiter.reset_rate_limit(test_identifier)
        if success:
            print("✅ Rate limit reset successfully")
        else:
            print("❌ Rate limit reset failed")
            return False
        
        # Test rate limit statistics
        stats = rate_limiter.get_rate_limit_stats()
        if stats:
            print(f"✅ Rate limit stats: {stats}")
        else:
            print("❌ Rate limit stats failed")
            return False
        
        print("🎉 Redis Rate Limiting tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        return False

def test_redis_queues():
    """Test Redis queues"""
    print("\n🧪 Testing Redis Queues...")
    print("=" * 50)
    
    try:
        from core.redis_queues import get_email_queue, get_ai_queue, get_crm_queue, get_webhook_queue
        
        # Test email queue
        email_queue = get_email_queue()
        
        if not email_queue.is_connected():
            print("❌ Email queue not connected")
            return False
        
        print("✅ Email queue connected successfully")
        
        # Test job enqueueing
        job_id = email_queue.enqueue_job(
            "send_email",
            {
                "to": "test@example.com",
                "subject": "Test Email",
                "body": "This is a test email"
            }
        )
        
        if job_id:
            print(f"✅ Email job enqueued: {job_id}")
        else:
            print("❌ Email job enqueueing failed")
            return False
        
        # Test job status
        job = email_queue.get_job_status(job_id)
        if job and str(job.status) == "JobStatus.PENDING":
            print("✅ Job status retrieved successfully")
        else:
            print("❌ Job status retrieval failed")
            return False
        
        # Test job completion
        success = email_queue.complete_job(job_id, {"success": True, "message_id": "msg_123"})
        if success:
            print("✅ Job completed successfully")
        else:
            print("❌ Job completion failed")
            return False
        
        # Test job result retrieval
        result = email_queue.get_job_result(job_id)
        if result and result.get("success"):
            print("✅ Job result retrieved successfully")
        else:
            print("❌ Job result retrieval failed")
            return False
        
        # Test queue statistics
        stats = email_queue.get_queue_stats()
        if stats:
            print(f"✅ Queue stats: {stats}")
        else:
            print("❌ Queue stats failed")
            return False
        
        # Test AI queue
        ai_queue = get_ai_queue()
        ai_job_id = ai_queue.enqueue_job(
            "process_ai_request",
            {
                "prompt": "How can I improve my business?",
                "user_id": "test_user"
            }
        )
        
        if ai_job_id:
            print(f"✅ AI job enqueued: {ai_job_id}")
        else:
            print("❌ AI job enqueueing failed")
            return False
        
        # Test CRM queue
        crm_queue = get_crm_queue()
        crm_job_id = crm_queue.enqueue_job(
            "update_crm",
            {
                "lead_data": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "company": "ABC Corp"
                }
            }
        )
        
        if crm_job_id:
            print(f"✅ CRM job enqueued: {crm_job_id}")
        else:
            print("❌ CRM job enqueueing failed")
            return False
        
        # Test webhook queue
        webhook_queue = get_webhook_queue()
        webhook_job_id = webhook_queue.enqueue_job(
            "process_webhook",
            {
                "webhook_data": {
                    "type": "stripe.payment.succeeded",
                    "data": {"amount": 1000, "currency": "usd"}
                }
            }
        )
        
        if webhook_job_id:
            print(f"✅ Webhook job enqueued: {webhook_job_id}")
        else:
            print("❌ Webhook job enqueueing failed")
            return False
        
        # Cleanup test jobs
        email_queue.clear_queue("jobs")
        ai_queue.clear_queue("jobs")
        crm_queue.clear_queue("jobs")
        webhook_queue.clear_queue("jobs")
        print("✅ Queue test data cleaned up")
        
        print("🎉 Redis Queues tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Queue test failed: {e}")
        return False

def test_integration():
    """Test integrated Redis features"""
    print("\n🧪 Testing Integrated Redis Features...")
    print("=" * 50)
    
    try:
        from core.redis_cache import get_cache
        from core.redis_sessions import get_session_manager
        from core.redis_rate_limiting import get_rate_limiter
        from core.redis_queues import get_email_queue
        
        # Test cache with session integration
        cache = get_cache()
        session_manager = get_session_manager()
        
        # Create a session
        user_id = "integration_test_user"
        user_data = {"name": "Integration Test", "email": "test@fikiri.com"}
        session_id = session_manager.create_session(user_id, user_data)
        
        if session_id:
            print("✅ Session created for integration test")
            
            # Cache AI response for this user
            cache.cache_ai_response(
                "What are the best practices for landscaping?",
                "Focus on soil health, proper plant selection, and regular maintenance.",
                user_id
            )
            print("✅ AI response cached for session user")
            
            # Test rate limiting for this user
            rate_limiter = get_rate_limiter()
            result = rate_limiter.check_rate_limit(f"user:{user_id}", 10, 60)
            if result['allowed']:
                print("✅ Rate limiting works with session user")
            else:
                print("❌ Rate limiting failed for session user")
                return False
            
            # Enqueue a job for this user
            email_queue = get_email_queue()
            job_id = email_queue.enqueue_job(
                "send_email",
                {
                    "to": user_data["email"],
                    "subject": "Welcome to Fikiri",
                    "body": "Thank you for joining Fikiri Solutions!"
                }
            )
            
            if job_id:
                print("✅ Email job enqueued for session user")
            else:
                print("❌ Email job enqueueing failed for session user")
                return False
            
            # Cleanup
            session_manager.delete_session(session_id)
            cache.clear_cache()
            email_queue.clear_queue("jobs")
            print("✅ Integration test cleanup completed")
        
        print("🎉 Integrated Redis Features tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Fikiri Solutions - Redis Integration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Redis Cache Layer", test_redis_cache),
        ("Redis Session Management", test_redis_sessions),
        ("Redis Rate Limiting", test_redis_rate_limiting),
        ("Redis Queues", test_redis_queues),
        ("Integrated Redis Features", test_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Redis integration tests passed!")
        print("\n✅ Your Redis Cloud database is ready for production with:")
        print("   🚀 High-performance caching")
        print("   🔐 Redis-backed sessions")
        print("   🛡️ Distributed rate limiting")
        print("   📋 Background job queues")
        print("   🧠 AI response caching")
        print("   📧 Email processing queues")
        print("   💼 CRM integration queues")
        print("   🔗 Webhook processing queues")
        
        print("\n🚀 Next Steps:")
        print("   1. Deploy your updated backend with Redis integration")
        print("   2. Start background workers for queue processing")
        print("   3. Monitor Redis performance and cache hit rates")
        print("   4. Scale your AI automation platform!")
        
        sys.exit(0)
    else:
        print(f"❌ {total - passed} tests failed. Check Redis configuration.")
        sys.exit(1)

if __name__ == "__main__":
    main()
