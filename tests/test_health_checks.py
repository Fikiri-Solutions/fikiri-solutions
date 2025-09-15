#!/usr/bin/env python3
"""
Fikiri Solutions - Health Check Tests
Unit tests for health endpoints and service validation.
"""

import unittest
import json
import time
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, services, initialize_services

class TestHealthChecks(unittest.TestCase):
    """Test health check endpoints."""
    
    def setUp(self):
        """Set up test client."""
        self.app = app
        self.client = app.test_client()
        self.app.config['TESTING'] = True
    
    def test_health_endpoint_exists(self):
        """Test that /api/health endpoint exists and returns 200."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('status', data)
        self.assertIn('timestamp', data)
        self.assertIn('version', data)
        self.assertIn('services', data)
    
    def test_health_endpoint_structure(self):
        """Test health endpoint returns proper structure."""
        response = self.client.get('/api/health')
        data = json.loads(response.data)
        
        # Check required fields
        required_fields = ['status', 'timestamp', 'version', 'services']
        for field in required_fields:
            self.assertIn(field, data, f"Missing required field: {field}")
        
        # Check status values
        valid_statuses = ['healthy', 'degraded', 'unhealthy']
        self.assertIn(data['status'], valid_statuses)
        
        # Check services structure
        self.assertIsInstance(data['services'], dict)
    
    def test_status_endpoint_exists(self):
        """Test that /api/status endpoint exists and returns 200."""
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('services', data)
    
    def test_services_endpoint_exists(self):
        """Test that /api/services endpoint exists and returns 200."""
        response = self.client.get('/api/services')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIsInstance(data, list)
        
        # Check service structure
        if data:
            service = data[0]
            required_fields = ['id', 'name', 'status', 'description']
            for field in required_fields:
                self.assertIn(field, service, f"Missing service field: {field}")
    
    def test_metrics_endpoint_exists(self):
        """Test that /api/metrics endpoint exists and returns 200."""
        response = self.client.get('/api/metrics')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        required_fields = ['totalEmails', 'activeLeads', 'aiResponses', 'avgResponseTime']
        for field in required_fields:
            self.assertIn(field, data, f"Missing metrics field: {field}")
    
    def test_activity_endpoint_exists(self):
        """Test that /api/activity endpoint exists and returns 200."""
        response = self.client.get('/api/activity')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIsInstance(data, list)
    
    def test_health_response_time(self):
        """Test that health endpoint responds within latency budget."""
        start_time = time.time()
        response = self.client.get('/api/health')
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        self.assertLess(response_time, 500, f"Health endpoint too slow: {response_time}ms")
    
    def test_services_response_time(self):
        """Test that services endpoint responds within latency budget."""
        start_time = time.time()
        response = self.client.get('/api/services')
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        self.assertLess(response_time, 500, f"Services endpoint too slow: {response_time}ms")
    
    def test_metrics_response_time(self):
        """Test that metrics endpoint responds within latency budget."""
        start_time = time.time()
        response = self.client.get('/api/metrics')
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        self.assertLess(response_time, 500, f"Metrics endpoint too slow: {response_time}ms")

class TestServiceHealth(unittest.TestCase):
    """Test individual service health checks."""
    
    def setUp(self):
        """Set up test client."""
        self.app = app
        self.client = app.test_client()
        self.app.config['TESTING'] = True
    
    @patch('app.services')
    def test_gmail_service_health(self, mock_services):
        """Test Gmail service health check."""
        # Mock Gmail service
        mock_gmail = MagicMock()
        mock_gmail.is_authenticated.return_value = True
        mock_services.__getitem__.return_value = mock_gmail
        
        response = self.client.get('/api/health')
        data = json.loads(response.data)
        
        self.assertIn('gmail', data['services'])
        gmail_status = data['services']['gmail']
        self.assertIn('status', gmail_status)
        self.assertIn('available', gmail_status)
    
    @patch('app.services')
    def test_ai_assistant_service_health(self, mock_services):
        """Test AI Assistant service health check."""
        # Mock AI Assistant service
        mock_ai = MagicMock()
        mock_ai.is_enabled.return_value = True
        mock_services.__getitem__.return_value = mock_ai
        
        response = self.client.get('/api/health')
        data = json.loads(response.data)
        
        self.assertIn('ai_assistant', data['services'])
        ai_status = data['services']['ai_assistant']
        self.assertIn('status', ai_status)
        self.assertIn('available', ai_status)

class TestErrorHandling(unittest.TestCase):
    """Test error handling in endpoints."""
    
    def setUp(self):
        """Set up test client."""
        self.app = app
        self.client = app.test_client()
        self.app.config['TESTING'] = True
    
    def test_invalid_endpoint_returns_404(self):
        """Test that invalid endpoints return 404."""
        response = self.client.get('/api/invalid-endpoint')
        self.assertEqual(response.status_code, 404)
    
    def test_health_endpoint_error_handling(self):
        """Test health endpoint handles errors gracefully."""
        with patch('app.services') as mock_services:
            # Mock service that raises an exception
            mock_services.__getitem__.side_effect = Exception("Service error")
            
            response = self.client.get('/api/health')
            self.assertEqual(response.status_code, 200)  # Should still return 200
            
            data = json.loads(response.data)
            self.assertIn('status', data)
            # Should handle errors gracefully

class TestLoadEndpoints(unittest.TestCase):
    """Test endpoints under simulated load."""
    
    def setUp(self):
        """Set up test client."""
        self.app = app
        self.client = app.test_client()
        self.app.config['TESTING'] = True
    
    def test_concurrent_health_checks(self):
        """Test multiple concurrent health check requests."""
        import threading
        import time
        
        results = []
        errors = []
        
        def make_request():
            try:
                start_time = time.time()
                response = self.client.get('/api/health')
                end_time = time.time()
                
                results.append({
                    'status_code': response.status_code,
                    'response_time': (end_time - start_time) * 1000
                })
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        self.assertEqual(len(errors), 0, f"Errors in concurrent requests: {errors}")
        self.assertEqual(len(results), 10, "Not all requests completed")
        
        # Check all requests succeeded
        for result in results:
            self.assertEqual(result['status_code'], 200)
            self.assertLess(result['response_time'], 1000, "Response time too slow under load")

def run_health_tests():
    """Run all health check tests."""
    print("🧪 Running Health Check Tests...")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestHealthChecks))
    suite.addTests(loader.loadTestsFromTestCase(TestServiceHealth))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestLoadEndpoints))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ All health check tests passed!")
        return True
    else:
        print(f"❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        return False

if __name__ == "__main__":
    success = run_health_tests()
    sys.exit(0 if success else 1)
