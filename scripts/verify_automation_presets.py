#!/usr/bin/env python3
"""
Verification script for automation presets functionality.

This script verifies:
1. Backend endpoints are accessible
2. Preset test endpoints work correctly
3. Execution logs are being recorded
4. Frontend can fetch logs and display them

Usage:
    python scripts/verify_automation_presets.py
"""

import sys
import os
import requests
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configuration
BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5000')
API_BASE = f'{BASE_URL}/api'

# Test credentials (update if needed)
TEST_EMAIL = os.getenv('TEST_EMAIL', 'admin@fikiri.com')
TEST_PASSWORD = os.getenv('TEST_PASSWORD', 'Admin123!')

# Preset IDs to test
PRESETS = [
    'gmail_crm',
    'lead_scoring',
    'slack_digest',
    'email_sheets',
    'calendar_followups'
]

def login():
    """Login and get session cookies"""
    print("🔐 Logging in...")
    session = requests.Session()
    response = session.post(
        f'{API_BASE}/auth/login',
        json={'email': TEST_EMAIL, 'password': TEST_PASSWORD},
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None
    
    print("✅ Login successful")
    return session

def check_endpoints(session):
    """Check if automation endpoints are accessible"""
    print("\n📡 Checking endpoints...")
    
    endpoints = {
        '/automation/rules': 'GET',
        '/automation/safety-status': 'GET',
        '/automation/logs': 'GET',
        '/automation/test': 'POST'
    }
    
    results = {}
    for endpoint, method in endpoints.items():
        try:
            if method == 'GET':
                response = session.get(f'{API_BASE}{endpoint}')
            else:
                # Just check if endpoint exists (will fail without payload, but that's OK)
                response = session.options(f'{API_BASE}{endpoint}')
            
            results[endpoint] = {
                'exists': response.status_code in [200, 400, 401, 405],  # 405 = method not allowed is OK
                'status': response.status_code
            }
        except Exception as e:
            results[endpoint] = {
                'exists': False,
                'error': str(e)
            }
    
    for endpoint, result in results.items():
        if result.get('exists'):
            print(f"  ✅ {endpoint} - Status: {result.get('status')}")
        else:
            print(f"  ❌ {endpoint} - Error: {result.get('error', 'Not found')}")
    
    return all(r.get('exists') for r in results.values())

def test_preset(session, preset_id):
    """Test a single preset"""
    print(f"\n🧪 Testing preset: {preset_id}")
    
    try:
        response = session.post(
            f'{API_BASE}/automation/test',
            json={'preset_id': preset_id},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"  ✅ Preset executed successfully")
                print(f"     Message: {data.get('message', 'No message')}")
                return True
            else:
                print(f"  ⚠️  Preset executed but returned success=false")
                print(f"     Error: {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"  ❌ Preset test failed: {response.status_code}")
            print(f"     Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error testing preset: {e}")
        return False

def check_logs(session, preset_id=None):
    """Check execution logs"""
    print(f"\n📋 Checking execution logs...")
    
    try:
        params = {'limit': 20}
        if preset_id:
            params['slug'] = preset_id
        
        response = session.get(
            f'{API_BASE}/automation/logs',
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            logs = data.get('data', {}).get('logs', []) or data.get('logs', [])
            
            print(f"  ✅ Found {len(logs)} log entries")
            
            if preset_id:
                filtered = [log for log in logs if log.get('slug') == preset_id]
                print(f"     {len(filtered)} entries for preset '{preset_id}'")
            
            # Show recent logs
            for log in logs[:5]:
                status = log.get('status', 'unknown')
                rule_name = log.get('rule_name', 'Unknown')
                executed_at = log.get('executed_at', 'Unknown')
                print(f"     - {rule_name}: {status} at {executed_at}")
            
            return True
        else:
            print(f"  ❌ Failed to fetch logs: {response.status_code}")
            print(f"     Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error fetching logs: {e}")
        return False

def verify_preset_rule_exists(session, preset_id):
    """Verify that a rule exists for the preset (needed for test endpoint)"""
    print(f"\n🔍 Checking if rule exists for preset: {preset_id}")
    
    try:
        response = session.get(f'{API_BASE}/automation/rules')
        
        if response.status_code == 200:
            data = response.json()
            rules = data.get('data', {}).get('rules', []) or data.get('rules', [])
            
            # Look for rule with matching slug
            matching = [r for r in rules if r.get('action_parameters', {}).get('slug') == preset_id]
            
            if matching:
                rule = matching[0]
                print(f"  ✅ Rule found: {rule.get('name')} (ID: {rule.get('id')}, Status: {rule.get('status')})")
                return True
            else:
                print(f"  ⚠️  No rule found for preset '{preset_id}'")
                print(f"     Note: You need to toggle the preset ON in the UI first")
                return False
        else:
            print(f"  ❌ Failed to fetch rules: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error checking rules: {e}")
        return False

def main():
    print("=" * 60)
    print("🔧 Automation Presets Verification Script")
    print("=" * 60)
    
    # Step 1: Login
    session = login()
    if not session:
        print("\n❌ Cannot proceed without authentication")
        sys.exit(1)
    
    # Step 2: Check endpoints
    if not check_endpoints(session):
        print("\n❌ Some endpoints are missing or inaccessible")
        sys.exit(1)
    
    # Step 3: Check logs endpoint
    check_logs(session)
    
    # Step 4: For each preset, verify rule exists and test
    print("\n" + "=" * 60)
    print("🧪 Testing Presets")
    print("=" * 60)
    
    results = {}
    for preset_id in PRESETS:
        print(f"\n📦 Preset: {preset_id}")
        
        # Check if rule exists
        rule_exists = verify_preset_rule_exists(session, preset_id)
        
        if rule_exists:
            # Test the preset
            test_result = test_preset(session, preset_id)
            results[preset_id] = {
                'rule_exists': True,
                'test_passed': test_result
            }
            
            # Wait a moment for logs to be written
            import time
            time.sleep(1)
            
            # Check logs for this preset
            check_logs(session, preset_id)
        else:
            results[preset_id] = {
                'rule_exists': False,
                'test_passed': False
            }
            print(f"  ⏭️  Skipping test (rule not found)")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    for preset_id, result in results.items():
        status = "✅" if result['test_passed'] else ("⚠️" if result['rule_exists'] else "⏭️")
        print(f"{status} {preset_id}: {'Test passed' if result['test_passed'] else ('Rule exists but test failed' if result['rule_exists'] else 'Rule not found')}")
    
    # Final check: Get all logs
    print("\n" + "=" * 60)
    print("📋 Final Log Check")
    print("=" * 60)
    check_logs(session)
    
    print("\n✅ Verification complete!")
    print("\n💡 Next steps:")
    print("   1. If any presets show 'Rule not found', toggle them ON in the UI")
    print("   2. Run tests from the UI using the 'Run Test' button")
    print("   3. Check the 'Recent executions' panel for log entries")
    print("   4. Verify status badges show 'Healthy' or 'Needs attention'")

if __name__ == '__main__':
    main()

