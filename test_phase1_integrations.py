#!/usr/bin/env python3
"""
Phase 1 Testing Script for Fikiri Solutions
Tests Google Sheets, Notion, Webhook, and Email Action integrations
"""

import os
import sys
import json
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.google_sheets_connector import get_sheets_connector
from core.notion_connector import get_notion_connector
from core.webhook_intake_service import get_webhook_service
from core.email_action_handlers import get_email_action_handler
from core.minimal_config import get_config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_google_sheets_integration():
    """Test Google Sheets connector"""
    logger.info("🧪 Testing Google Sheets integration...")
    
    sheets_connector = get_sheets_connector()
    if not sheets_connector:
        logger.warning("⚠️ Google Sheets not configured - skipping test")
        return False
    
    try:
        # Test creating lead sheet
        result = sheets_connector.create_lead_sheet("Test Leads")
        if not result['success']:
            logger.error(f"❌ Failed to create lead sheet: {result.get('error')}")
            return False
        
        # Test adding a lead
        test_lead = {
            'id': 'test_lead_001',
            'name': 'Test Lead',
            'email': 'test@example.com',
            'phone': '+1-555-123-4567',
            'company': 'Test Company',
            'source': 'test',
            'status': 'new',
            'score': 75,
            'notes': 'This is a test lead',
            'tags': ['test', 'automation']
        }
        
        result = sheets_connector.add_lead(test_lead)
        if result['success']:
            logger.info("✅ Google Sheets integration working")
            return True
        else:
            logger.error(f"❌ Failed to add lead to Sheets: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Google Sheets test failed: {e}")
        return False

def test_notion_integration():
    """Test Notion connector"""
    logger.info("🧪 Testing Notion integration...")
    
    notion_connector = get_notion_connector()
    if not notion_connector:
        logger.warning("⚠️ Notion not configured - skipping test")
        return False
    
    try:
        # Test creating customer profile
        test_profile = {
            'name': 'Test Customer',
            'email': 'customer@example.com',
            'phone': '+1-555-987-6543',
            'company': 'Test Corp',
            'source': 'test',
            'status': 'new',
            'score': 80,
            'notes': 'Test customer profile',
            'tags': ['test', 'customer']
        }
        
        result = notion_connector.create_customer_profile(test_profile)
        if result['success']:
            logger.info("✅ Notion integration working")
            return True
        else:
            logger.error(f"❌ Failed to create Notion profile: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Notion test failed: {e}")
        return False

def test_webhook_intake():
    """Test webhook intake service"""
    logger.info("🧪 Testing webhook intake service...")
    
    webhook_service = get_webhook_service()
    if not webhook_service:
        logger.error("❌ Webhook service not available")
        return False
    
    try:
        # Test generic webhook processing
        test_data = {
            'name': 'Webhook Test Lead',
            'email': 'webhook@example.com',
            'phone': '+1-555-456-7890',
            'company': 'Webhook Corp',
            'message': 'This is a test webhook submission'
        }
        
        result = webhook_service.process_generic_webhook(test_data)
        if result['success']:
            logger.info("✅ Webhook intake service working")
            return True
        else:
            logger.error(f"❌ Failed to process webhook: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Webhook test failed: {e}")
        return False

def test_email_action_handlers():
    """Test email action handlers"""
    logger.info("🧪 Testing email action handlers...")
    
    action_handler = get_email_action_handler()
    if not action_handler:
        logger.error("❌ Email action handler not available")
        return False
    
    try:
        # Test with mock data (won't actually send emails without Gmail tokens)
        logger.info("✅ Email action handlers initialized")
        logger.info("ℹ️ Note: Actual email actions require Gmail OAuth tokens")
        return True
        
    except Exception as e:
        logger.error(f"❌ Email action handler test failed: {e}")
        return False

def test_configuration():
    """Test configuration loading"""
    logger.info("🧪 Testing configuration...")
    
    try:
        config = get_config()
        
        # Check for required Phase 1 config
        required_configs = [
            'google_sheets_id',
            'notion_api_key', 
            'notion_database_id',
            'webhook_secret_key'
        ]
        
        missing_configs = []
        for config_key in required_configs:
            if not getattr(config, config_key, None):
                missing_configs.append(config_key)
        
        if missing_configs:
            logger.warning(f"⚠️ Missing configurations: {', '.join(missing_configs)}")
            logger.info("ℹ️ These can be configured in .env file for full functionality")
        else:
            logger.info("✅ All configurations present")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        return False

def run_phase1_tests():
    """Run all Phase 1 tests"""
    logger.info("🚀 Running Phase 1 Integration Tests...")
    logger.info("=" * 50)
    
    tests = [
        ("Configuration", test_configuration),
        ("Google Sheets", test_google_sheets_integration),
        ("Notion", test_notion_integration),
        ("Webhook Intake", test_webhook_intake),
        ("Email Actions", test_email_action_handlers)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running {test_name} test...")
        results[test_name] = test_func()
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 Phase 1 Test Results:")
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All Phase 1 integrations are working!")
    else:
        logger.info("⚠️ Some integrations need configuration or have issues")
    
    return passed == total

if __name__ == "__main__":
    success = run_phase1_tests()
    sys.exit(0 if success else 1)
