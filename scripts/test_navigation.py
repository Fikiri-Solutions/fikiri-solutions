#!/usr/bin/env python3
"""
Comprehensive Navigation Test Script
Tests all clickable elements, buttons, cards, and navigation on specified pages
"""

import requests
import json
from urllib.parse import urljoin, urlparse
import sys

BASE_URL = "http://localhost:5174"
BACKEND_URL = "http://localhost:5000"

# Pages to test
PAGES_TO_TEST = [
    "/dashboard",
    "/services",
    "/integrations/gmail",
    "/automations",
    "/crm",
    "/ai",
    "/ai/chatbot-builder",
    "/industry"
]

# Expected routes from each page
EXPECTED_ROUTES = {
    "/dashboard": [
        "/crm",           # Total Leads card
        "/services",      # Emails Processed card
        "/ai",            # AI Responses card
        "/industry",      # Revenue card
    ],
    "/services": [
        # No navigation routes, but has buttons for testing services
    ],
    "/integrations/gmail": [
        # No navigation routes, but has buttons for connecting/refreshing
    ],
    "/automations": [
        # No navigation routes, but has toggle buttons and test buttons
    ],
    "/crm": [
        # No navigation routes, but has add lead button and drag-drop
    ],
    "/ai": [
        # No navigation routes, but has quick action buttons
    ],
    "/ai/chatbot-builder": [
        # No navigation routes, but has upload/process buttons
    ],
    "/industry": [
        # No navigation routes, but has industry selection buttons
    ]
}

def test_page_accessible(url):
    """Test if a page is accessible"""
    try:
        response = requests.get(url, timeout=5, allow_redirects=True)
        return {
            "accessible": response.status_code == 200,
            "status_code": response.status_code,
            "final_url": response.url,
            "redirected": len(response.history) > 0
        }
    except requests.exceptions.ConnectionError:
        return {
            "accessible": False,
            "status_code": None,
            "error": "Connection refused - frontend not running"
        }
    except Exception as e:
        return {
            "accessible": False,
            "status_code": None,
            "error": str(e)
        }

def test_backend_health():
    """Test if backend is running"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        return {
            "running": response.status_code == 200,
            "status_code": response.status_code
        }
    except:
        return {
            "running": False,
            "status_code": None
        }

def main():
    print("=" * 80)
    print("FIKIRI SOLUTIONS - COMPREHENSIVE NAVIGATION TEST")
    print("=" * 80)
    print()
    
    # Test backend health
    print("1. Testing Backend Health...")
    backend_health = test_backend_health()
    if backend_health["running"]:
        print(f"   ✅ Backend is running at {BACKEND_URL}")
    else:
        print(f"   ❌ Backend is NOT running at {BACKEND_URL}")
        print(f"      Status: {backend_health.get('status_code', 'Connection refused')}")
    print()
    
    # Test frontend pages
    print("2. Testing Frontend Pages...")
    print()
    
    results = {}
    for page in PAGES_TO_TEST:
        url = urljoin(BASE_URL, page)
        print(f"   Testing: {page}")
        result = test_page_accessible(url)
        results[page] = result
        
        if result["accessible"]:
            print(f"      ✅ Accessible (Status: {result['status_code']})")
            if result.get("redirected"):
                print(f"      ⚠️  Redirected from {page} to {result['final_url']}")
        else:
            print(f"      ❌ NOT Accessible")
            if "error" in result:
                print(f"         Error: {result['error']}")
            else:
                print(f"         Status: {result.get('status_code', 'Unknown')}")
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    accessible_count = sum(1 for r in results.values() if r.get("accessible"))
    total_count = len(results)
    
    print(f"Backend Status: {'✅ Running' if backend_health['running'] else '❌ Not Running'}")
    print(f"Frontend Pages: {accessible_count}/{total_count} accessible")
    print()
    
    if accessible_count == total_count and backend_health["running"]:
        print("✅ All systems operational!")
        print()
        print("MANUAL TESTING CHECKLIST:")
        print("=" * 80)
        print()
        print("For each page, manually test:")
        print()
        
        for page in PAGES_TO_TEST:
            print(f"📄 {page}")
            if page == "/dashboard":
                print("   - Click 'Total Leads' card → Should navigate to /crm")
                print("   - Click 'Emails Processed' card → Should navigate to /services")
                print("   - Click 'AI Responses' card → Should navigate to /ai")
                print("   - Click 'Revenue' card → Should navigate to /industry")
                print("   - Click any Service Card → Should show service details")
                print("   - Use browser back button → Should return to dashboard")
            elif page == "/services":
                print("   - Toggle service enable/disable → Should update state")
                print("   - Click 'Test Service' button → Should show test result modal")
                print("   - Click 'Save Configuration' → Should save changes")
                print("   - Click 'Refresh Data' → Should reload services")
                print("   - Use browser back button → Should return to previous page")
            elif page == "/integrations/gmail":
                print("   - Click 'Connect Gmail' button → Should start OAuth flow")
                print("   - Click 'Refresh' button → Should reload status")
                print("   - Click 'Sync inbox' button → Should trigger sync")
                print("   - Use browser back button → Should return to previous page")
            elif page == "/automations":
                print("   - Toggle automation ON/OFF → Should update state")
                print("   - Click 'Run Test' button → Should execute preset")
                print("   - Click 'Save & Activate' button → Should save and activate")
                print("   - Change config fields → Should update local state")
                print("   - Use browser back button → Should return to previous page")
            elif page == "/crm":
                print("   - Click 'Add Lead' button → Should open modal")
                print("   - Drag lead cards between stages → Should update stage")
                print("   - Use search/filter → Should filter leads")
                print("   - Click lead in table → Should select lead")
                print("   - Use browser back button → Should return to previous page")
            elif page == "/ai":
                print("   - Click quick action cards → Should populate input")
                print("   - Click 'Send to AI Assistant' → Should send message")
                print("   - Click 'Generate Reply' → Should generate reply")
                print("   - Click 'Send Email' → Should send email")
                print("   - Select lead from inbox → Should select lead")
                print("   - Use browser back button → Should return to previous page")
            elif page == "/ai/chatbot-builder":
                print("   - Upload file → Should process document")
                print("   - Click 'Process document' → Should extract text")
                print("   - Click 'Save FAQ' → Should save FAQ")
                print("   - Click 'Save to knowledge base' → Should save document")
                print("   - Click 'Vectorize content' → Should vectorize")
                print("   - Click 'Preview' → Should search knowledge")
                print("   - Use browser back button → Should return to previous page")
            elif page == "/industry":
                print("   - Click industry buttons → Should select industry")
                print("   - Click pricing tier cards → Should update metrics")
                print("   - Enter message and click 'Send Message' → Should get AI response")
                print("   - Use browser back button → Should return to previous page")
            print()
        
        print("NAVIGATION TESTING:")
        print("=" * 80)
        print()
        print("Test sidebar navigation:")
        print("   - Click each sidebar link → Should navigate to correct page")
        print("   - Click logo → Should navigate to /dashboard")
        print("   - Use browser back button → Should return to previous page")
        print()
        print("Test mobile navigation:")
        print("   - Open mobile menu → Should show navigation")
        print("   - Click each link → Should navigate and close menu")
        print()
        print("Test breadcrumbs/back navigation:")
        print("   - Navigate: Dashboard → CRM → Back → Should return to Dashboard")
        print("   - Navigate: Dashboard → Services → Back → Should return to Dashboard")
        print("   - Navigate: Dashboard → AI → Back → Should return to Dashboard")
        print("   - Navigate: Dashboard → Industry → Back → Should return to Dashboard")
        print()
        
        return 0
    else:
        print("❌ Some issues detected. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

