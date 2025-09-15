#!/usr/bin/env python3
"""
Fikiri Solutions - Comprehensive Stability Test Suite
Tests environment validation, health checks, load testing, and monitoring.
"""

import asyncio
import subprocess
import sys
import os
import time
import json
from pathlib import Path

class StabilityTestSuite:
    """Comprehensive stability testing for Fikiri Solutions."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.results = {
            'environment_validation': False,
            'health_checks': False,
            'load_testing': False,
            'code_quality': False,
            'monitoring': False
        }
    
    def run_all_tests(self) -> bool:
        """Run all stability tests."""
        print("🛡️  Fikiri Solutions - Stability Test Suite")
        print("=" * 60)
        
        # 1. Environment Validation
        print("\n1️⃣ Environment Validation")
        print("-" * 30)
        self.results['environment_validation'] = self.test_environment_validation()
        
        # 2. Health Checks
        print("\n2️⃣ Health Checks")
        print("-" * 30)
        self.results['health_checks'] = self.test_health_checks()
        
        # 3. Load Testing
        print("\n3️⃣ Load Testing")
        print("-" * 30)
        self.results['load_testing'] = self.test_load_testing()
        
        # 4. Code Quality
        print("\n4️⃣ Code Quality")
        print("-" * 30)
        self.results['code_quality'] = self.test_code_quality()
        
        # 5. Monitoring
        print("\n5️⃣ Monitoring")
        print("-" * 30)
        self.results['monitoring'] = self.test_monitoring()
        
        # Summary
        self.print_summary()
        
        return all(self.results.values())
    
    def test_environment_validation(self) -> bool:
        """Test environment validation script."""
        try:
            script_path = self.project_root / "scripts" / "validate_environment.py"
            if not script_path.exists():
                print("❌ Environment validation script not found")
                return False
            
            # Run environment validation
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                print("✅ Environment validation passed")
                return True
            else:
                print("❌ Environment validation failed:")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ Error running environment validation: {e}")
            return False
    
    def test_health_checks(self) -> bool:
        """Test health check endpoints."""
        try:
            script_path = self.project_root / "tests" / "test_health_checks.py"
            if not script_path.exists():
                print("❌ Health check tests not found")
                return False
            
            # Run health check tests
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                print("✅ Health check tests passed")
                return True
            else:
                print("❌ Health check tests failed:")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ Error running health check tests: {e}")
            return False
    
    def test_load_testing(self) -> bool:
        """Test load testing framework."""
        try:
            script_path = self.project_root / "scripts" / "load_test.py"
            if not script_path.exists():
                print("❌ Load testing script not found")
                return False
            
            # Run load test (comprehensive)
            result = subprocess.run(
                [sys.executable, str(script_path), "--test-type", "comprehensive"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print("✅ Load testing passed")
                return True
            else:
                print("❌ Load testing failed:")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Load testing timed out")
            return False
        except Exception as e:
            print(f"❌ Error running load testing: {e}")
            return False
    
    def test_code_quality(self) -> bool:
        """Test code quality tools."""
        try:
            script_path = self.project_root / "scripts" / "code_quality.py"
            if not script_path.exists():
                print("❌ Code quality script not found")
                return False
            
            # Run code quality checks
            result = subprocess.run(
                [sys.executable, str(script_path), "--all"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                print("✅ Code quality checks passed")
                return True
            else:
                print("❌ Code quality checks failed:")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ Error running code quality checks: {e}")
            return False
    
    def test_monitoring(self) -> bool:
        """Test monitoring and logging."""
        try:
            # Test structured logging
            test_script = """
import sys
sys.path.insert(0, '.')
from core.structured_logging import logger, monitor, error_handler
from core.performance_monitoring import performance_monitor

# Test logging
logger.info("Test log message", test_data="example")
logger.warning("Test warning", warning_code="TEST")
logger.error("Test error", error_code="TEST_ERROR")

# Test monitoring
monitor.track_request('test', '/api/test', 'GET', 0.1, 200)
monitor.track_service_health('test_service', True, 0.05)

# Test error handling
try:
    raise ValueError("Test error")
except Exception as e:
    error_handler.handle_error(e, 'test_context', 'Test error message')

# Test performance monitoring
performance_monitor.track_operation('test_operation', 150.5, True)

print("✅ Monitoring tests completed successfully")
"""
            
            result = subprocess.run(
                [sys.executable, "-c", test_script],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                print("✅ Monitoring tests passed")
                return True
            else:
                print("❌ Monitoring tests failed:")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ Error running monitoring tests: {e}")
            return False
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📊 STABILITY TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.results)
        passed_tests = sum(self.results.values())
        
        for test_name, passed in self.results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All stability tests passed! System is ready for production.")
        else:
            print("⚠️  Some stability tests failed. Review and fix issues before deployment.")
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        if not self.results['environment_validation']:
            print("• Fix environment variable configuration")
        if not self.results['health_checks']:
            print("• Fix health check endpoints and service initialization")
        if not self.results['load_testing']:
            print("• Optimize performance and add caching/queuing")
        if not self.results['code_quality']:
            print("• Fix code quality issues (formatting, linting, security)")
        if not self.results['monitoring']:
            print("• Fix monitoring and logging configuration")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fikiri Solutions Stability Test Suite")
    parser.add_argument("--test", choices=[
        "environment", "health", "load", "quality", "monitoring", "all"
    ], default="all", help="Specific test to run")
    
    args = parser.parse_args()
    
    suite = StabilityTestSuite()
    
    if args.test == "all":
        success = suite.run_all_tests()
    elif args.test == "environment":
        success = suite.test_environment_validation()
    elif args.test == "health":
        success = suite.test_health_checks()
    elif args.test == "load":
        success = suite.test_load_testing()
    elif args.test == "quality":
        success = suite.test_code_quality()
    elif args.test == "monitoring":
        success = suite.test_monitoring()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
