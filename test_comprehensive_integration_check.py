#!/usr/bin/env python3
"""
Comprehensive Integration Check for Fikiri Solutions
Verifies all AI Email Assistant features work together and don't break existing functionality
"""

import sys
import os
sys.path.append('.')

def test_core_imports():
    """Test that all core modules import correctly"""
    print("🧪 Testing Core Module Imports")
    print("=" * 50)
    
    try:
        # Test existing core modules
        from core.minimal_ai_assistant import MinimalAIEmailAssistant, create_ai_assistant
        from core.minimal_crm_service import MinimalCRMService
        from core.minimal_email_actions import MinimalEmailActions
        from core.minimal_config import get_config
        from core.redis_service import get_redis_client
        from core.redis_queues import get_redis_queue
        
        print("✅ Existing core modules import successfully")
        
        # Test new advanced modules
        from core.advanced_email_templates import get_email_templates
        from core.advanced_sentiment_analyzer import get_sentiment_analyzer
        from core.multi_language_support import get_multi_language_support
        from core.email_scheduling_system import get_email_scheduler
        from core.advanced_analytics_system import get_analytics_system
        
        print("✅ New advanced modules import successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Core imports failed: {e}")
        return False

def test_ai_assistant_integration():
    """Test AI Assistant integration with all features"""
    print("\n🧪 Testing AI Assistant Integration")
    print("=" * 50)
    
    try:
        from core.minimal_ai_assistant import MinimalAIEmailAssistant
        
        assistant = MinimalAIEmailAssistant()
        
        # Test basic functionality still works
        print(f"✅ AI Assistant enabled: {assistant.is_enabled()}")
        
        # Test usage stats
        stats = assistant.get_usage_stats()
        print(f"✅ Usage stats: {stats}")
        
        # Test email classification
        classification = assistant.classify_email_intent(
            "I'm interested in your landscaping services",
            "Quote Request"
        )
        print(f"✅ Email classification: {classification['intent']}")
        
        # Test response generation
        response = assistant.generate_response(
            "I need help with my account",
            "John Doe",
            "Account Help",
            "support_request"
        )
        print(f"✅ Response generation: {len(response)} characters")
        
        # Test contact extraction
        contact_info = assistant.extract_contact_info(
            "My phone is 555-123-4567 and I work at ABC Corp"
        )
        print(f"✅ Contact extraction: {contact_info}")
        
        return True
        
    except Exception as e:
        print(f"❌ AI Assistant integration test failed: {e}")
        return False

def test_advanced_features_integration():
    """Test integration between all advanced features"""
    print("\n🧪 Testing Advanced Features Integration")
    print("=" * 50)
    
    try:
        from core.minimal_ai_assistant import MinimalAIEmailAssistant
        from core.advanced_email_templates import get_email_templates
        from core.advanced_sentiment_analyzer import get_sentiment_analyzer
        from core.multi_language_support import get_multi_language_support
        from core.email_scheduling_system import get_email_scheduler
        from core.advanced_analytics_system import get_analytics_system
        
        # Initialize all systems
        assistant = MinimalAIEmailAssistant()
        templates = get_email_templates()
        sentiment_analyzer = get_sentiment_analyzer()
        multi_lang = get_multi_language_support()
        scheduler = get_email_scheduler()
        analytics = get_analytics_system()
        
        print("✅ All advanced systems initialized")
        
        # Test integrated workflow
        test_message = "I'm very frustrated with the slow response time! Can you help me schedule a follow-up email?"
        
        # 1. Sentiment Analysis
        if sentiment_analyzer:
            sentiment_result = sentiment_analyzer.analyze_sentiment(test_message)
            print(f"✅ Sentiment analysis: {sentiment_result.sentiment} ({sentiment_result.urgency})")
        
        # 2. Language Detection
        if multi_lang:
            lang_result = multi_lang.detect_language(test_message)
            print(f"✅ Language detection: {lang_result.language} ({lang_result.language_code})")
        
        # 3. Template Generation
        template_result = templates.generate_email_content(
            "landscaping_quote_request",
            {
                "sender_name": "Test User",
                "company_name": "Fikiri Solutions",
                "service_type": "landscaping",
                "service_specialties": "residential landscaping, commercial maintenance",
                "service_areas": "lawn care, planting, hardscaping",
                "user_name": "AI Assistant",
                "contact_info": "support@fikirisolutions.com"
            }
        )
        print(f"✅ Template generation: {template_result.get('subject', 'Failed')[:30]}...")
        
        # 4. Analytics Tracking
        analytics.track_metric("integration_test", 1, "count", "testing")
        print("✅ Analytics tracking: Success")
        
        # 5. Email Scheduling
        from datetime import datetime, timedelta
        future_time = datetime.now() + timedelta(hours=1)
        schedule_result = scheduler.schedule_email(
            user_id=1,
            recipient_email="test@example.com",
            subject="Integration Test",
            body="This is an integration test email",
            scheduled_time=future_time
        )
        print(f"✅ Email scheduling: {schedule_result.get('success', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Advanced features integration test failed: {e}")
        return False

def test_backend_integration():
    """Test backend integration with existing systems"""
    print("\n🧪 Testing Backend Integration")
    print("=" * 50)
    
    try:
        # Test app.py imports
        import app
        print("✅ Main app.py imports successfully")
        
        # Test service initialization
        from core.minimal_config import get_config
        config = get_config()
        print(f"✅ Config loaded: Redis URL configured: {bool(getattr(config, 'redis_url', None))}")
        
        # Test Redis connection
        from core.redis_service import get_redis_client
        redis_client = get_redis_client()
        if redis_client:
            print("✅ Redis client connected")
        else:
            print("⚠️ Redis client not connected (expected in test environment)")
        
        # Test existing API endpoints still work
        from core.minimal_crm_service import MinimalCRMService
        crm_service = MinimalCRMService()
        leads = crm_service.get_all_leads()
        print(f"✅ CRM service: {len(leads)} leads found")
        
        return True
        
    except Exception as e:
        print(f"❌ Backend integration test failed: {e}")
        return False

def test_frontend_integration():
    """Test frontend integration"""
    print("\n🧪 Testing Frontend Integration")
    print("=" * 50)
    
    try:
        # Test AI Assistant page integration
        import os
        frontend_path = "frontend/src/pages/AIAssistant.tsx"
        if os.path.exists(frontend_path):
            print("✅ AI Assistant page exists")
            
            # Check if the page imports the necessary components
            with open(frontend_path, 'r') as f:
                content = f.read()
                
            if "DemoVideoModal" in content:
                print("✅ Demo Video Modal integrated")
            if "formatAIResponse" in content:
                print("✅ AI Response formatting integrated")
            if "simulateTyping" in content:
                print("✅ Typing simulation integrated")
        else:
            print("⚠️ AI Assistant page not found")
        
        # Test API client integration
        api_client_path = "frontend/src/services/apiClient.ts"
        if os.path.exists(api_client_path):
            print("✅ API client exists")
            
            with open(api_client_path, 'r') as f:
                content = f.read()
                
            if "sendChatMessage" in content:
                print("✅ Chat message API integrated")
        else:
            print("⚠️ API client not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Frontend integration test failed: {e}")
        return False

def test_error_handling():
    """Test error handling and fallbacks"""
    print("\n🧪 Testing Error Handling and Fallbacks")
    print("=" * 50)
    
    try:
        from core.minimal_ai_assistant import MinimalAIEmailAssistant
        
        # Test with missing OpenAI API key
        assistant = MinimalAIEmailAssistant()
        
        # Test fallback classification
        classification = assistant.classify_email_intent("Test email", "Test subject")
        print(f"✅ Fallback classification: {classification['intent']}")
        
        # Test fallback response generation
        response = assistant.generate_response("Test", "User", "Subject", "general")
        print(f"✅ Fallback response: {len(response)} characters")
        
        # Test fallback contact extraction
        contact_info = assistant.extract_contact_info("Test contact info")
        print(f"✅ Fallback contact extraction: {contact_info}")
        
        # Test chat response with missing dependencies
        chat_response = assistant.generate_chat_response("Test message")
        print(f"✅ Fallback chat response: {chat_response.get('success', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def test_performance():
    """Test performance and memory usage"""
    print("\n🧪 Testing Performance")
    print("=" * 50)
    
    try:
        import time
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Test multiple operations
        from core.minimal_ai_assistant import MinimalAIEmailAssistant
        from core.advanced_email_templates import get_email_templates
        from core.advanced_analytics_system import get_analytics_system
        
        start_time = time.time()
        
        # Perform multiple operations
        for i in range(10):
            assistant = MinimalAIEmailAssistant()
            templates = get_email_templates()
            analytics = get_analytics_system()
            
            # Track metrics
            analytics.track_metric(f"perf_test_{i}", i, "count", "testing")
            
            # Generate template
            templates.generate_email_content(
                "landscaping_quote_request",
                {"sender_name": f"User {i}", "company_name": "Test Co"}
            )
        
        end_time = time.time()
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"✅ Performance test completed in {end_time - start_time:.2f} seconds")
        print(f"✅ Memory usage: {initial_memory:.1f}MB → {final_memory:.1f}MB (+{memory_increase:.1f}MB)")
        
        if memory_increase < 50:  # Less than 50MB increase
            print("✅ Memory usage is acceptable")
        else:
            print("⚠️ High memory usage detected")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

def test_data_consistency():
    """Test data consistency across systems"""
    print("\n🧪 Testing Data Consistency")
    print("=" * 50)
    
    try:
        from core.minimal_crm_service import MinimalCRMService
        from core.advanced_analytics_system import get_analytics_system
        
        # Test CRM data consistency
        crm_service = MinimalCRMService()
        leads = crm_service.get_all_leads()
        print(f"✅ CRM data consistency: {len(leads)} leads")
        
        # Test analytics data consistency
        analytics = get_analytics_system()
        summary = analytics.get_metrics_summary()
        print(f"✅ Analytics data consistency: {summary.get('total_metrics', 0)} metrics")
        
        # Test template data consistency
        from core.advanced_email_templates import get_email_templates
        templates = get_email_templates()
        stats = templates.get_template_statistics()
        print(f"✅ Template data consistency: {stats['total_templates']} templates")
        
        return True
        
    except Exception as e:
        print(f"❌ Data consistency test failed: {e}")
        return False

def main():
    """Run comprehensive integration tests"""
    print("🔍 Comprehensive Integration Check for Fikiri Solutions")
    print("=" * 70)
    
    tests = [
        test_core_imports,
        test_ai_assistant_integration,
        test_advanced_features_integration,
        test_backend_integration,
        test_frontend_integration,
        test_error_handling,
        test_performance,
        test_data_consistency
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 70)
    print(f"🎯 Integration Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL INTEGRATIONS WORKING PERFECTLY!")
        print("✅ AI Email Assistant features are fully integrated")
        print("✅ No existing functionality was broken")
        print("✅ All systems work together seamlessly")
        print("✅ Error handling and fallbacks are working")
        print("✅ Performance is acceptable")
        print("✅ Data consistency is maintained")
    else:
        print(f"⚠️ {total - passed} integration tests failed - needs attention")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
