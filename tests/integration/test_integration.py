"""
Integration Tests for Fikiri Solutions
Comprehensive integration testing suite
"""

import pytest
import requests
import json
import time
from typing import Dict, Any, List
import subprocess
import os
import signal
import threading

class IntegrationTestSuite:
    """Comprehensive integration test suite"""
    
    def __init__(self, frontend_url: str = "http://localhost:3000", backend_url: str = "http://localhost:8081"):
        self.frontend_url = frontend_url
        self.backend_url = backend_url
        self.session = requests.Session()
        self.test_data = {}
    
    def setup_test_environment(self):
        """Setup test environment"""
        # Start backend if not running
        if not self._is_backend_running():
            self._start_backend()
            time.sleep(5)
        
        # Start frontend if not running
        if not self._is_frontend_running():
            self._start_frontend()
            time.sleep(10)
    
    def _is_backend_running(self) -> bool:
        """Check if backend is running"""
        try:
            response = requests.get(f"{self.backend_url}/api/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _is_frontend_running(self) -> bool:
        """Check if frontend is running"""
        try:
            response = requests.get(self.frontend_url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _start_backend(self):
        """Start backend server"""
        # This would start the backend in a subprocess
        # For now, we'll assume it's already running
        pass
    
    def _start_frontend(self):
        """Start frontend server"""
        # This would start the frontend in a subprocess
        # For now, we'll assume it's already running
        pass
    
    def test_backend_health(self):
        """Test backend health endpoint"""
        response = self.session.get(f"{self.backend_url}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] in ['healthy', 'degraded']
        return data
    
    def test_frontend_loading(self):
        """Test frontend loads correctly"""
        response = self.session.get(self.frontend_url)
        assert response.status_code == 200
        assert 'Fikiri Solutions' in response.text
        return response.text
    
    def test_api_endpoints_integration(self):
        """Test API endpoints integration"""
        endpoints = [
            '/api/health',
            '/api/services',
            '/api/metrics',
            '/api/activity'
        ]
        
        for endpoint in endpoints:
            response = self.session.get(f"{self.backend_url}{endpoint}")
            assert response.status_code in [200, 503]  # 503 is acceptable for some services
            if response.status_code == 200:
                data = response.json()
                assert 'success' in data or 'status' in data
    
    def test_crm_integration(self):
        """Test CRM integration"""
        # Test getting leads
        response = self.session.get(f"{self.backend_url}/api/crm/leads")
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert 'success' in data
            assert 'data' in data
    
    def test_ai_assistant_integration(self):
        """Test AI Assistant integration"""
        # Test AI chat endpoint
        chat_data = {
            'message': 'Hello, test message',
            'context': {'conversation_history': []}
        }
        
        response = self.session.post(
            f"{self.backend_url}/api/ai/chat",
            json=chat_data
        )
        
        assert response.status_code in [200, 503]  # 503 if AI service unavailable
        
        if response.status_code == 200:
            data = response.json()
            assert 'success' in data
            assert 'data' in data
    
    def test_performance_monitoring_integration(self):
        """Test performance monitoring integration"""
        endpoints = [
            '/api/performance/summary',
            '/api/performance/system-health',
            '/api/performance/export'
        ]
        
        for endpoint in endpoints:
            response = self.session.get(f"{self.backend_url}{endpoint}")
            assert response.status_code == 200
            data = response.json()
            assert 'success' in data
            assert 'data' in data
    
    def test_database_integration(self):
        """Test database integration"""
        endpoints = [
            '/api/database/stats',
            '/api/database/query-performance',
            '/api/database/migrations'
        ]
        
        for endpoint in endpoints:
            response = self.session.get(f"{self.backend_url}{endpoint}")
            assert response.status_code == 200
            data = response.json()
            assert 'success' in data
            assert 'data' in data
    
    def test_business_operations_integration(self):
        """Test business operations integration"""
        # Test analytics
        response = self.session.get(f"{self.backend_url}/business/analytics/summary")
        assert response.status_code == 200
        data = response.json()
        assert 'success' in data
        
        # Test KPI dashboard
        response = self.session.get(f"{self.backend_url}/business/kpi/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert 'success' in data
        
        # Test legal pages
        legal_pages = [
            '/business/privacy-policy',
            '/business/terms-of-service',
            '/business/cookie-policy'
        ]
        
        for page in legal_pages:
            response = self.session.get(f"{self.backend_url}{page}")
            assert response.status_code == 200
            assert 'Fikiri Solutions' in response.text
    
    def test_frontend_backend_integration(self):
        """Test frontend-backend integration"""
        # Test that frontend can communicate with backend
        # This would typically involve testing API calls from the frontend
        
        # For now, we'll test that both services are running
        assert self._is_frontend_running()
        assert self._is_backend_running()
        
        # Test CORS headers
        response = self.session.options(f"{self.backend_url}/api/health")
        assert 'Access-Control-Allow-Origin' in response.headers
    
    def test_error_handling_integration(self):
        """Test error handling integration"""
        # Test 404 endpoint
        response = self.session.get(f"{self.backend_url}/api/nonexistent")
        assert response.status_code == 404
        
        # Test invalid data
        response = self.session.post(
            f"{self.backend_url}/api/crm/leads",
            json={'invalid': 'data'}
        )
        assert response.status_code == 400
        data = response.json()
        assert 'success' in data
        assert data['success'] == False
    
    def test_security_integration(self):
        """Test security integration"""
        # Test rate limiting (if implemented)
        # Test CORS headers
        response = self.session.get(f"{self.backend_url}/api/health")
        assert 'Access-Control-Allow-Origin' in response.headers
        
        # Test that sensitive endpoints require authentication
        response = self.session.get(f"{self.backend_url}/api/auth/status")
        # This should either require auth or return appropriate error
        assert response.status_code in [200, 401, 403]
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests"""
        results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_results': []
        }
        
        test_methods = [
            'test_backend_health',
            'test_frontend_loading',
            'test_api_endpoints_integration',
            'test_crm_integration',
            'test_ai_assistant_integration',
            'test_performance_monitoring_integration',
            'test_database_integration',
            'test_business_operations_integration',
            'test_frontend_backend_integration',
            'test_error_handling_integration',
            'test_security_integration'
        ]
        
        for test_method in test_methods:
            results['total_tests'] += 1
            try:
                getattr(self, test_method)()
                results['passed_tests'] += 1
                results['test_results'].append({
                    'test': test_method,
                    'status': 'passed',
                    'error': None
                })
            except Exception as e:
                results['failed_tests'] += 1
                results['test_results'].append({
                    'test': test_method,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results

pytestmark = pytest.mark.integration


def _integration_enabled() -> bool:
    return os.getenv("RUN_INTEGRATION_TESTS") == "1"


# Pytest integration tests
@pytest.fixture
def integration_suite():
    """Pytest fixture for integration test suite"""
    if not _integration_enabled():
        pytest.skip("Integration tests disabled. Set RUN_INTEGRATION_TESTS=1")
    suite = IntegrationTestSuite()
    suite.setup_test_environment()
    return suite

def test_backend_health(integration_suite):
    """Test backend health"""
    integration_suite.test_backend_health()

def test_frontend_loading(integration_suite):
    """Test frontend loading"""
    integration_suite.test_frontend_loading()

def test_api_endpoints(integration_suite):
    """Test API endpoints"""
    integration_suite.test_api_endpoints_integration()

def test_crm_integration(integration_suite):
    """Test CRM integration"""
    integration_suite.test_crm_integration()

def test_ai_assistant(integration_suite):
    """Test AI Assistant integration"""
    integration_suite.test_ai_assistant_integration()

def test_performance_monitoring(integration_suite):
    """Test performance monitoring"""
    integration_suite.test_performance_monitoring_integration()

def test_database_integration(integration_suite):
    """Test database integration"""
    integration_suite.test_database_integration()

def test_business_operations(integration_suite):
    """Test business operations"""
    integration_suite.test_business_operations_integration()

def test_frontend_backend_integration(integration_suite):
    """Test frontend-backend integration"""
    integration_suite.test_frontend_backend_integration()

def test_error_handling(integration_suite):
    """Test error handling"""
    integration_suite.test_error_handling_integration()

def test_security_integration(integration_suite):
    """Test security integration"""
    integration_suite.test_security_integration()

if __name__ == "__main__":
    # Run integration tests directly
    suite = IntegrationTestSuite()
    suite.setup_test_environment()
    results = suite.run_all_tests()
    
    print(f"\n📊 Integration Test Results:")
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed_tests']}")
    print(f"Failed: {results['failed_tests']}")
    print(f"Success Rate: {(results['passed_tests'] / results['total_tests'] * 100):.1f}%")
    
    if results['failed_tests'] > 0:
        print(f"\n❌ Failed Tests:")
        for result in results['test_results']:
            if result['status'] == 'failed':
                print(f"  {result['test']}: {result['error']}")
    
    exit(0 if results['failed_tests'] == 0 else 1)
