#!/usr/bin/env python3
"""
Comprehensive Test Runner for Fikiri Solutions
Runs all tests and generates coverage reports
"""

import subprocess
import sys
import os
import json
import time
from typing import Dict, Any, List

class TestRunner:
    """Comprehensive test runner"""
    
    def __init__(self):
        self.results = {
            'frontend': {},
            'backend': {},
            'integration': {},
            'e2e': {},
            'coverage': {},
            'summary': {}
        }
    
    def run_frontend_tests(self) -> Dict[str, Any]:
        """Run frontend tests"""
        print("🧪 Running frontend tests...")
        
        frontend_dir = "frontend"
        if not os.path.exists(frontend_dir):
            return {'error': 'Frontend directory not found'}
        
        results = {}
        
        try:
            # Run unit tests
            print("  Running unit tests...")
            result = subprocess.run(
                ['npm', 'run', 'test'],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            results['unit_tests'] = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            # Run type check
            print("  Running type check...")
            result = subprocess.run(
                ['npm', 'run', 'type-check'],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            results['type_check'] = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            # Run linting
            print("  Running linting...")
            result = subprocess.run(
                ['npm', 'run', 'lint'],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            results['linting'] = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            # Run build test
            print("  Testing build...")
            result = subprocess.run(
                ['npm', 'run', 'build'],
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            results['build'] = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            results['error'] = 'Frontend tests timed out'
        except Exception as e:
            results['error'] = str(e)
        
        return results
    
    def run_backend_tests(self) -> Dict[str, Any]:
        """Run backend tests"""
        print("🐍 Running backend tests...")
        
        results = {}
        
        try:
            # Run unit tests with coverage
            print("  Running unit tests with coverage...")
            result = subprocess.run([
                'python', '-m', 'pytest', 
                'tests/', 
                '-v', 
                '--cov=core', 
                '--cov=app', 
                '--cov-report=xml', 
                '--cov-report=html',
                '--cov-report=term'
            ], capture_output=True, text=True, timeout=300)
            
            results['unit_tests'] = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            # Run security tests
            print("  Running security tests...")
            result = subprocess.run([
                'bandit', '-r', 'core/', 'app.py', '-f', 'json'
            ], capture_output=True, text=True, timeout=60)
            
            results['security_tests'] = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            # Run type checking
            print("  Running type checking...")
            result = subprocess.run([
                'python', '-m', 'mypy', 'core/', 'app.py', '--ignore-missing-imports'
            ], capture_output=True, text=True, timeout=120)
            
            results['type_check'] = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            results['error'] = 'Backend tests timed out'
        except Exception as e:
            results['error'] = str(e)
        
        return results
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests"""
        print("🔗 Running integration tests...")
        
        results = {}
        
        try:
            # Run integration tests
            result = subprocess.run([
                'python', '-m', 'pytest', 
                'tests/integration/', 
                '-v', 
                '--tb=short'
            ], capture_output=True, text=True, timeout=300)
            
            results['integration_tests'] = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            # Run API endpoint tests
            print("  Running API endpoint tests...")
            result = subprocess.run([
                'python', 'scripts/test_api_endpoints.py', 'http://localhost:8081'
            ], capture_output=True, text=True, timeout=120)
            
            results['api_tests'] = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            results['error'] = 'Integration tests timed out'
        except Exception as e:
            results['error'] = str(e)
        
        return results
    
    def run_e2e_tests(self) -> Dict[str, Any]:
        """Run end-to-end tests"""
        print("🌐 Running E2E tests...")
        
        frontend_dir = "frontend"
        if not os.path.exists(frontend_dir):
            return {'error': 'Frontend directory not found'}
        
        results = {}
        
        try:
            # Run Cypress E2E tests
            result = subprocess.run([
                'npm', 'run', 'e2e'
            ], cwd=frontend_dir, capture_output=True, text=True, timeout=600)
            
            results['cypress_tests'] = {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            results['error'] = 'E2E tests timed out'
        except Exception as e:
            results['error'] = str(e)
        
        return results
    
    def generate_coverage_report(self) -> Dict[str, Any]:
        """Generate comprehensive coverage report"""
        print("📊 Generating coverage report...")
        
        coverage_data = {}
        
        # Backend coverage
        if os.path.exists('coverage.xml'):
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse('coverage.xml')
                root = tree.getroot()
                
                coverage_data['backend'] = {
                    'line_rate': float(root.get('line-rate', 0)),
                    'branch_rate': float(root.get('branch-rate', 0)),
                    'lines_covered': int(root.get('lines-covered', 0)),
                    'lines_valid': int(root.get('lines-valid', 0))
                }
            except Exception as e:
                coverage_data['backend'] = {'error': str(e)}
        
        # Frontend coverage (if available)
        frontend_coverage_dir = "frontend/coverage"
        if os.path.exists(frontend_coverage_dir):
            coverage_data['frontend'] = {
                'coverage_dir': frontend_coverage_dir,
                'status': 'available'
            }
        
        return coverage_data
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests"""
        print("🚀 Starting comprehensive test suite...")
        start_time = time.time()
        
        # Run all test suites
        self.results['frontend'] = self.run_frontend_tests()
        self.results['backend'] = self.run_backend_tests()
        self.results['integration'] = self.run_integration_tests()
        self.results['e2e'] = self.run_e2e_tests()
        self.results['coverage'] = self.generate_coverage_report()
        
        # Generate summary
        end_time = time.time()
        self.results['summary'] = self._generate_summary(end_time - start_time)
        
        return self.results
    
    def _generate_summary(self, total_time: float) -> Dict[str, Any]:
        """Generate test summary"""
        summary = {
            'total_time': round(total_time, 2),
            'frontend_success': self._check_success(self.results['frontend']),
            'backend_success': self._check_success(self.results['backend']),
            'integration_success': self._check_success(self.results['integration']),
            'e2e_success': self._check_success(self.results['e2e']),
            'overall_success': True
        }
        
        # Check overall success
        for key in ['frontend_success', 'backend_success', 'integration_success', 'e2e_success']:
            if not summary[key]:
                summary['overall_success'] = False
                break
        
        return summary
    
    def _check_success(self, results: Dict[str, Any]) -> bool:
        """Check if test results indicate success"""
        if 'error' in results:
            return False
        
        for key, value in results.items():
            if isinstance(value, dict) and 'success' in value:
                if not value['success']:
                    return False
        
        return True
    
    def print_report(self):
        """Print comprehensive test report"""
        print("\n" + "="*60)
        print("📊 COMPREHENSIVE TEST REPORT")
        print("="*60)
        
        summary = self.results['summary']
        print(f"\n⏱️  Total Time: {summary['total_time']}s")
        print(f"🎯 Overall Success: {'✅' if summary['overall_success'] else '❌'}")
        
        print(f"\n📋 Test Suite Results:")
        print(f"  Frontend: {'✅' if summary['frontend_success'] else '❌'}")
        print(f"  Backend: {'✅' if summary['backend_success'] else '❌'}")
        print(f"  Integration: {'✅' if summary['integration_success'] else '❌'}")
        print(f"  E2E: {'✅' if summary['e2e_success'] else '❌'}")
        
        # Coverage information
        if 'backend' in self.results['coverage']:
            backend_coverage = self.results['coverage']['backend']
            if 'line_rate' in backend_coverage:
                print(f"\n📈 Coverage:")
                print(f"  Backend Line Coverage: {backend_coverage['line_rate']:.1%}")
                print(f"  Backend Branch Coverage: {backend_coverage['branch_rate']:.1%}")
        
        # Error details
        print(f"\n❌ Errors:")
        for suite_name, suite_results in self.results.items():
            if suite_name == 'summary':
                continue
            
            if 'error' in suite_results:
                print(f"  {suite_name}: {suite_results['error']}")
            
            for test_name, test_result in suite_results.items():
                if isinstance(test_result, dict) and 'success' in test_result and not test_result['success']:
                    print(f"  {suite_name}.{test_name}: Failed")
        
        print("\n" + "="*60)

def main():
    """Main function"""
    runner = TestRunner()
    results = runner.run_all_tests()
    runner.print_report()
    
    # Exit with appropriate code
    if results['summary']['overall_success']:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()

