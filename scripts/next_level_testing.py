#!/usr/bin/env python3
"""
Fikiri Solutions - Next-Level Enterprise Testing Suite
Comprehensive testing for chaos testing, red team security, onboarding, and documentation
"""

import asyncio
import time
import logging
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent / "scripts"))

# Import our testing modules
try:
    from chaos_testing import run_chaos_testing
    from red_team_security import run_red_team_security_test
    from user_onboarding_test import run_user_onboarding_test
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all testing scripts are in the scripts/ directory")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('next_level_testing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NextLevelTestRunner:
    """Comprehensive next-level enterprise testing runner."""
    
    def __init__(self):
        self.results = {
            "start_time": datetime.now().isoformat(),
            "tests": {},
            "summary": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "success_rate": 0.0,
                "total_duration": 0.0
            },
            "recommendations": []
        }
    
    async def run_chaos_testing_suite(self) -> Dict[str, Any]:
        """Run chaos testing and failover drills."""
        logger.info("🚀 Starting Chaos Testing & Failover Drills...")
        
        start_time = time.time()
        
        try:
            results = await run_chaos_testing()
            
            duration = time.time() - start_time
            
            test_result = {
                "name": "Chaos Testing & Failover Drills",
                "success": results.get("final_report", {}).get("summary", {}).get("success_rate", 0) >= 80,
                "duration_seconds": duration,
                "details": results,
                "recommendations": self._generate_chaos_recommendations(results)
            }
            
            logger.info(f"✅ Chaos testing completed in {duration:.1f}s")
            return test_result
            
        except Exception as e:
            logger.error(f"❌ Chaos testing failed: {e}")
            return {
                "name": "Chaos Testing & Failover Drills",
                "success": False,
                "duration_seconds": time.time() - start_time,
                "error": str(e),
                "recommendations": ["Fix chaos testing implementation", "Check system dependencies"]
            }
    
    async def run_red_team_security_suite(self) -> Dict[str, Any]:
        """Run red team security testing."""
        logger.info("🔒 Starting Red Team Security Testing...")
        
        start_time = time.time()
        
        try:
            results = await run_red_team_security_test()
            
            duration = time.time() - start_time
            
            vulnerabilities = results.get("summary", {}).get("vulnerabilities_found", 0)
            critical_vulns = results.get("summary", {}).get("critical_vulnerabilities", 0)
            
            test_result = {
                "name": "Red Team Security Testing",
                "success": critical_vulns == 0 and vulnerabilities < 5,  # No critical vulns, <5 total
                "duration_seconds": duration,
                "details": results,
                "recommendations": results.get("recommendations", [])
            }
            
            logger.info(f"✅ Security testing completed in {duration:.1f}s - {vulnerabilities} vulnerabilities found")
            return test_result
            
        except Exception as e:
            logger.error(f"❌ Security testing failed: {e}")
            return {
                "name": "Red Team Security Testing",
                "success": False,
                "duration_seconds": time.time() - start_time,
                "error": str(e),
                "recommendations": ["Fix security testing implementation", "Check network connectivity"]
            }
    
    async def run_onboarding_test_suite(self) -> Dict[str, Any]:
        """Run user onboarding dry run tests."""
        logger.info("👤 Starting User Onboarding Dry Run Tests...")
        
        start_time = time.time()
        
        try:
            results = await run_user_onboarding_test()
            
            duration = time.time() - start_time
            
            success_rate = results.get("summary", {}).get("success_rate", 0)
            target_met = results.get("summary", {}).get("target_met", False)
            
            test_result = {
                "name": "User Onboarding Dry Run Tests",
                "success": success_rate >= 90 and target_met,  # 90% success rate and under 5 minutes
                "duration_seconds": duration,
                "details": results,
                "recommendations": results.get("recommendations", [])
            }
            
            logger.info(f"✅ Onboarding testing completed in {duration:.1f}s - {success_rate:.1f}% success rate")
            return test_result
            
        except Exception as e:
            logger.error(f"❌ Onboarding testing failed: {e}")
            return {
                "name": "User Onboarding Dry Run Tests",
                "success": False,
                "duration_seconds": time.time() - start_time,
                "error": str(e),
                "recommendations": ["Fix onboarding testing implementation", "Check API endpoints"]
            }
    
    def run_documentation_sprint(self) -> Dict[str, Any]:
        """Run documentation sprint validation."""
        logger.info("📚 Starting Documentation Sprint Validation...")
        
        start_time = time.time()
        
        try:
            # Check if documentation files exist
            docs_dir = Path("docs")
            required_docs = [
                "SYSTEM_ARCHITECTURE.md",
                "CLIENT_ONBOARDING_GUIDE.md"
            ]
            
            existing_docs = []
            missing_docs = []
            
            for doc in required_docs:
                doc_path = docs_dir / doc
                if doc_path.exists():
                    existing_docs.append(doc)
                else:
                    missing_docs.append(doc)
            
            # Check documentation quality
            doc_quality_score = 0
            quality_checks = []
            
            for doc in existing_docs:
                doc_path = docs_dir / doc
                content = doc_path.read_text()
                
                # Check for key sections
                if doc == "SYSTEM_ARCHITECTURE.md":
                    required_sections = [
                        "System Overview",
                        "Architecture Components", 
                        "API Documentation",
                        "Database Schema",
                        "Security Implementation",
                        "Deployment Architecture",
                        "Troubleshooting Guide"
                    ]
                else:  # CLIENT_ONBOARDING_GUIDE.md
                    required_sections = [
                        "Quick Start Checklist",
                        "Step 1: Account Setup",
                        "Step 2: Gmail Connection",
                        "Step 3: CRM Configuration",
                        "Step 4: Automation Setup",
                        "Step 5: First Email Test",
                        "Troubleshooting",
                        "Best Practices"
                    ]
                
                doc_sections = [section for section in required_sections if section in content]
                section_score = len(doc_sections) / len(required_sections)
                doc_quality_score += section_score
                
                quality_checks.append({
                    "document": doc,
                    "sections_found": len(doc_sections),
                    "sections_total": len(required_sections),
                    "quality_score": section_score
                })
            
            overall_quality = doc_quality_score / len(existing_docs) if existing_docs else 0
            
            duration = time.time() - start_time
            
            test_result = {
                "name": "Documentation Sprint Validation",
                "success": len(missing_docs) == 0 and overall_quality >= 0.8,  # All docs exist and 80% quality
                "duration_seconds": duration,
                "details": {
                    "existing_docs": existing_docs,
                    "missing_docs": missing_docs,
                    "quality_checks": quality_checks,
                    "overall_quality": overall_quality
                },
                "recommendations": self._generate_docs_recommendations(missing_docs, overall_quality)
            }
            
            logger.info(f"✅ Documentation validation completed in {duration:.1f}s - {overall_quality:.1%} quality")
            return test_result
            
        except Exception as e:
            logger.error(f"❌ Documentation validation failed: {e}")
            return {
                "name": "Documentation Sprint Validation",
                "success": False,
                "duration_seconds": time.time() - start_time,
                "error": str(e),
                "recommendations": ["Fix documentation validation", "Check file permissions"]
            }
    
    def _generate_chaos_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on chaos testing results."""
        recommendations = []
        
        final_report = results.get("final_report", {})
        success_rate = final_report.get("summary", {}).get("success_rate", 0)
        
        if success_rate < 90:
            recommendations.append("Improve system resilience - chaos testing success rate below 90%")
        
        recovery_times = final_report.get("recovery_times", [])
        if recovery_times:
            avg_recovery = sum(recovery_times) / len(recovery_times)
            if avg_recovery > 60:
                recommendations.append("Reduce recovery times - average recovery time exceeds 60 seconds")
        
        recommendations.extend([
            "Implement automated failover procedures",
            "Add circuit breakers for external dependencies",
            "Implement graceful degradation strategies",
            "Add health check endpoints for all services",
            "Implement automated recovery procedures"
        ])
        
        return recommendations
    
    def _generate_docs_recommendations(self, missing_docs: List[str], quality: float) -> List[str]:
        """Generate recommendations based on documentation validation."""
        recommendations = []
        
        if missing_docs:
            recommendations.append(f"Create missing documentation: {', '.join(missing_docs)}")
        
        if quality < 0.8:
            recommendations.append("Improve documentation quality - add missing sections and details")
        
        recommendations.extend([
            "Add code examples to API documentation",
            "Include troubleshooting scenarios",
            "Add performance benchmarks",
            "Include security best practices",
            "Add deployment guides for different environments"
        ])
        
        return recommendations
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all next-level enterprise tests."""
        logger.info("🚀 Starting Next-Level Enterprise Testing Suite...")
        
        overall_start_time = time.time()
        
        # Run all test suites
        test_suites = [
            ("chaos_testing", self.run_chaos_testing_suite()),
            ("red_team_security", self.run_red_team_security_suite()),
            ("user_onboarding", self.run_onboarding_test_suite()),
            ("documentation_sprint", self.run_documentation_sprint())
        ]
        
        for suite_name, test_coroutine in test_suites:
            logger.info(f"🔄 Running {suite_name}...")
            
            if asyncio.iscoroutine(test_coroutine):
                result = await test_coroutine
            else:
                result = test_coroutine
            
            self.results["tests"][suite_name] = result
            
            # Update summary
            self.results["summary"]["total_tests"] += 1
            if result["success"]:
                self.results["summary"]["passed_tests"] += 1
            else:
                self.results["summary"]["failed_tests"] += 1
            
            # Add recommendations
            if "recommendations" in result:
                self.results["recommendations"].extend(result["recommendations"])
        
        # Calculate final summary
        total_duration = time.time() - overall_start_time
        self.results["summary"]["total_duration"] = total_duration
        self.results["summary"]["success_rate"] = (
            self.results["summary"]["passed_tests"] / self.results["summary"]["total_tests"] * 100
            if self.results["summary"]["total_tests"] > 0 else 0
        )
        
        self.results["end_time"] = datetime.now().isoformat()
        
        # Generate overall recommendations
        self.results["overall_recommendations"] = self._generate_overall_recommendations()
        
        logger.info(f"🎯 Next-level testing complete:")
        logger.info(f"   Total tests: {self.results['summary']['total_tests']}")
        logger.info(f"   Passed: {self.results['summary']['passed_tests']}")
        logger.info(f"   Failed: {self.results['summary']['failed_tests']}")
        logger.info(f"   Success rate: {self.results['summary']['success_rate']:.1f}%")
        logger.info(f"   Total duration: {total_duration:.1f}s")
        
        return self.results
    
    def _generate_overall_recommendations(self) -> List[str]:
        """Generate overall recommendations based on all test results."""
        recommendations = []
        
        success_rate = self.results["summary"]["success_rate"]
        
        if success_rate < 100:
            recommendations.append("Address failed tests to achieve 100% success rate")
        
        if success_rate < 80:
            recommendations.append("Critical: Multiple test failures require immediate attention")
        
        # Add specific recommendations based on failed tests
        for test_name, test_result in self.results["tests"].items():
            if not test_result["success"]:
                recommendations.append(f"Fix {test_name} - {test_result.get('error', 'Unknown error')}")
        
        # Add general enterprise recommendations
        recommendations.extend([
            "Implement continuous monitoring and alerting",
            "Set up automated testing in CI/CD pipeline",
            "Create incident response procedures",
            "Implement disaster recovery plans",
            "Regular security audits and penetration testing",
            "Performance monitoring and optimization",
            "User experience testing and optimization",
            "Documentation maintenance and updates"
        ])
        
        return recommendations
    
    def save_results(self, filename: str = None) -> str:
        """Save test results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"next_level_test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"📄 Test results saved to {filename}")
        return filename
    
    def print_summary(self):
        """Print a formatted summary of test results."""
        print("\n" + "="*80)
        print("🚀 NEXT-LEVEL ENTERPRISE TESTING SUITE RESULTS")
        print("="*80)
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total Tests: {self.results['summary']['total_tests']}")
        print(f"   Passed: {self.results['summary']['passed_tests']}")
        print(f"   Failed: {self.results['summary']['failed_tests']}")
        print(f"   Success Rate: {self.results['summary']['success_rate']:.1f}%")
        print(f"   Total Duration: {self.results['summary']['total_duration']:.1f}s")
        
        print(f"\n🧪 TEST RESULTS:")
        for test_name, test_result in self.results["tests"].items():
            status = "✅ PASS" if test_result["success"] else "❌ FAIL"
            duration = test_result["duration_seconds"]
            print(f"   {status} {test_result['name']} ({duration:.1f}s)")
            
            if not test_result["success"] and "error" in test_result:
                print(f"      Error: {test_result['error']}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        for i, recommendation in enumerate(self.results["recommendations"], 1):
            print(f"   {i}. {recommendation}")
        
        print(f"\n🎯 OVERALL RECOMMENDATIONS:")
        for i, recommendation in enumerate(self.results["overall_recommendations"], 1):
            print(f"   {i}. {recommendation}")
        
        print("\n" + "="*80)

async def main():
    """Main function to run all next-level tests."""
    print("🚀 Starting Next-Level Enterprise Testing Suite...")
    print("This will run comprehensive tests for:")
    print("  • Chaos Testing & Failover Drills")
    print("  • Red Team Security Testing") 
    print("  • User Onboarding Dry Run Tests")
    print("  • Documentation Sprint Validation")
    print()
    
    runner = NextLevelTestRunner()
    
    try:
        results = await runner.run_all_tests()
        
        # Save results
        filename = runner.save_results()
        
        # Print summary
        runner.print_summary()
        
        # Return appropriate exit code
        if results["summary"]["success_rate"] == 100:
            print("\n🎉 All tests passed! Your system is enterprise-ready!")
            return 0
        elif results["summary"]["success_rate"] >= 80:
            print("\n⚠️ Most tests passed, but some issues need attention.")
            return 1
        else:
            print("\n❌ Multiple test failures require immediate attention.")
            return 2
            
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        print(f"\n❌ Test suite failed: {e}")
        return 3

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
