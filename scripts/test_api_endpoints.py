#!/usr/bin/env python3
"""
Comprehensive API Testing Script
Tests all API endpoints for Fikiri Solutions
"""

import requests
import json
import time
import sys
from typing import Dict, Any, List

class APITester:
    """Comprehensive API testing suite"""
    
    def __init__(self, base_url: str = "http://localhost:8081"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results: List[Dict[str, Any]] = []
        self.session_token = None
    
    def test_endpoint(self, method: str, endpoint: str, data: Dict[str, Any] = None, 
                     expected_status: int = 200, auth_required: bool = False) -> Dict[str, Any]:
        """Test a single API endpoint"""
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        if auth_required and self.session_token:
            headers['Authorization'] = f"Bearer {self.session_token}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, headers=headers)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, headers=headers)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            result = {
                'endpoint': endpoint,
                'method': method,
                'status_code': response.status_code,
                'expected_status': expected_status,
                'success': response.status_code == expected_status,
                'response_time': response.elapsed.total_seconds(),
                'response_size': len(response.content)
            }
            
            try:
                result['response_data'] = response.json()
            except:
                result['response_data'] = response.text[:200]
            
            if not result['success']:
                result['error'] = f"Expected {expected_status}, got {response.status_code}"
            
        except Exception as e:
            result = {
                'endpoint': endpoint,
                'method': method,
                'success': False,
                'error': str(e),
                'response_time': 0
            }
        
        self.test_results.append(result)
        return result
    
    def run_all_tests(self):
        """Run comprehensive API tests"""
        print("🚀 Starting comprehensive API testing...")
        
        # Health and status endpoints
        print("\n📊 Testing health and status endpoints...")
        self.test_endpoint('GET', '/api/health')
        self.test_endpoint('GET', '/api/services')
        self.test_endpoint('GET', '/api/metrics')
        self.test_endpoint('GET', '/api/activity')
        
        # Authentication endpoints
        print("\n🔐 Testing authentication endpoints...")
        self.test_endpoint('POST', '/api/auth/login', {
            'email': 'test@example.com',
            'password': 'password123'
        })
        
        # CRM endpoints
        print("\n👥 Testing CRM endpoints...")
        self.test_endpoint('GET', '/api/crm/leads')
        self.test_endpoint('POST', '/api/crm/leads', {
            'name': 'Test Lead',
            'email': 'testlead@example.com',
            'company': 'Test Company'
        })
        
        # AI Assistant endpoints
        print("\n🤖 Testing AI Assistant endpoints...")
        self.test_endpoint('POST', '/api/ai/chat', {
            'message': 'Hello, how can you help me?',
            'context': {'conversation_history': []}
        })
        
        # Performance monitoring endpoints
        print("\n📈 Testing performance monitoring endpoints...")
        self.test_endpoint('GET', '/api/performance/summary')
        self.test_endpoint('GET', '/api/performance/system-health')
        self.test_endpoint('GET', '/api/performance/export')
        
        # Database optimization endpoints
        print("\n🗄️ Testing database optimization endpoints...")
        self.test_endpoint('GET', '/api/database/stats')
        self.test_endpoint('GET', '/api/database/query-performance')
        self.test_endpoint('GET', '/api/database/migrations')
        
        # Business operations endpoints
        print("\n💼 Testing business operations endpoints...")
        self.test_endpoint('GET', '/business/analytics/summary')
        self.test_endpoint('GET', '/business/kpi/dashboard')
        self.test_endpoint('POST', '/business/analytics/track', {
            'event_type': 'test_event',
            'properties': {'test': True}
        })
        
        # Legal pages
        print("\n📄 Testing legal pages...")
        self.test_endpoint('GET', '/business/privacy-policy')
        self.test_endpoint('GET', '/business/terms-of-service')
        self.test_endpoint('GET', '/business/cookie-policy')
        
        # Versioned API endpoints
        print("\n🔄 Testing versioned API endpoints...")
        self.test_endpoint('GET', '/api/v1/status')
        self.test_endpoint('GET', '/api/v2/status')
        
        # Async operations
        print("\n⚡ Testing async operations...")
        bulk_result = self.test_endpoint('POST', '/api/async/bulk-process')
        if bulk_result.get('success') and 'task_id' in bulk_result.get('response_data', {}):
            task_id = bulk_result['response_data']['task_id']
            time.sleep(2)  # Wait for task to start
            self.test_endpoint('GET', f'/api/tasks/{task_id}')
        
        # Cache operations
        print("\n💾 Testing cache operations...")
        self.test_endpoint('POST', '/api/cache/clear')
        
        # Industry-specific endpoints
        print("\n🏭 Testing industry-specific endpoints...")
        self.test_endpoint('GET', '/api/industry/prompts')
        self.test_endpoint('POST', '/api/industry/chat', {
            'industry': 'landscaping',
            'client_id': 'test_client',
            'message': 'Help with lead management'
        })
        
        # Test endpoints
        print("\n🧪 Testing test endpoints...")
        self.test_endpoint('POST', '/api/test/email-parser')
        self.test_endpoint('POST', '/api/test/crm')
        self.test_endpoint('POST', '/api/test/ai-assistant')
        self.test_endpoint('GET', '/api/test/openai-key')
        
        print("\n✅ API testing completed!")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result.get('success', False))
        failed_tests = total_tests - successful_tests
        
        # Calculate average response time
        response_times = [r.get('response_time', 0) for r in self.test_results if r.get('response_time')]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Group results by category
        categories = {}
        for result in self.test_results:
            endpoint = result['endpoint']
            if '/api/health' in endpoint:
                category = 'Health & Status'
            elif '/api/auth' in endpoint:
                category = 'Authentication'
            elif '/api/crm' in endpoint:
                category = 'CRM'
            elif '/api/ai' in endpoint:
                category = 'AI Assistant'
            elif '/api/performance' in endpoint:
                category = 'Performance'
            elif '/api/database' in endpoint:
                category = 'Database'
            elif '/business' in endpoint:
                category = 'Business Operations'
            elif '/api/v' in endpoint:
                category = 'Versioned API'
            elif '/api/async' in endpoint:
                category = 'Async Operations'
            elif '/api/cache' in endpoint:
                category = 'Cache'
            elif '/api/industry' in endpoint:
                category = 'Industry Specific'
            elif '/api/test' in endpoint:
                category = 'Test Endpoints'
            else:
                category = 'Other'
            
            if category not in categories:
                categories[category] = {'total': 0, 'successful': 0, 'failed': 0}
            
            categories[category]['total'] += 1
            if result.get('success', False):
                categories[category]['successful'] += 1
            else:
                categories[category]['failed'] += 1
        
        report = {
            'summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'failed_tests': failed_tests,
                'success_rate': (successful_tests / total_tests * 100) if total_tests > 0 else 0,
                'average_response_time': round(avg_response_time, 3)
            },
            'categories': categories,
            'failed_tests': [r for r in self.test_results if not r.get('success', False)],
            'slow_tests': [r for r in self.test_results if r.get('response_time', 0) > 1.0],
            'test_results': self.test_results
        }
        
        return report
    
    def print_report(self):
        """Print formatted test report"""
        report = self.generate_report()
        
        print("\n" + "="*60)
        print("📊 API TESTING REPORT")
        print("="*60)
        
        print(f"\n📈 SUMMARY:")
        print(f"  Total Tests: {report['summary']['total_tests']}")
        print(f"  Successful: {report['summary']['successful_tests']}")
        print(f"  Failed: {report['summary']['failed_tests']}")
        print(f"  Success Rate: {report['summary']['success_rate']:.1f}%")
        print(f"  Avg Response Time: {report['summary']['average_response_time']}s")
        
        print(f"\n📋 BY CATEGORY:")
        for category, stats in report['categories'].items():
            success_rate = (stats['successful'] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"  {category}: {stats['successful']}/{stats['total']} ({success_rate:.1f}%)")
        
        if report['failed_tests']:
            print(f"\n❌ FAILED TESTS:")
            for test in report['failed_tests']:
                print(f"  {test['method']} {test['endpoint']}: {test.get('error', 'Unknown error')}")
        
        if report['slow_tests']:
            print(f"\n🐌 SLOW TESTS (>1s):")
            for test in report['slow_tests']:
                print(f"  {test['method']} {test['endpoint']}: {test['response_time']:.2f}s")
        
        print("\n" + "="*60)

def main():
    """Main function"""
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8081"
    
    tester = APITester(base_url)
    tester.run_all_tests()
    tester.print_report()
    
    # Exit with error code if any tests failed
    report = tester.generate_report()
    if report['summary']['failed_tests'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()

