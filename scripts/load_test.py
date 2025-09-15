#!/usr/bin/env python3
"""
Fikiri Solutions - Load Testing Framework
Simulates high load to test system performance and identify bottlenecks.
"""

import asyncio
import aiohttp
import time
import json
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass
import argparse
import sys

@dataclass
class LoadTestResult:
    """Results from a load test."""
    endpoint: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    errors: List[str]

class LoadTester:
    """Load testing framework for Fikiri Solutions."""
    
    def __init__(self, base_url: str = "http://localhost:8081"):
        self.base_url = base_url
        self.session = None
        self.results: List[LoadTestResult] = []
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def test_endpoint(self, endpoint: str, method: str = "GET", 
                          concurrent_users: int = 10, requests_per_user: int = 50,
                          payload: Dict[str, Any] = None) -> LoadTestResult:
        """Test a single endpoint under load."""
        print(f"🚀 Testing {method} {endpoint} with {concurrent_users} users, {requests_per_user} requests each...")
        
        start_time = time.time()
        response_times = []
        errors = []
        successful_requests = 0
        failed_requests = 0
        
        async def make_request():
            nonlocal successful_requests, failed_requests
            try:
                request_start = time.time()
                
                if method.upper() == "GET":
                    async with self.session.get(f"{self.base_url}{endpoint}") as response:
                        await response.text()
                elif method.upper() == "POST":
                    async with self.session.post(
                        f"{self.base_url}{endpoint}",
                        json=payload or {}
                    ) as response:
                        await response.text()
                
                request_end = time.time()
                response_time = (request_end - request_start) * 1000  # Convert to ms
                response_times.append(response_time)
                successful_requests += 1
                
            except Exception as e:
                failed_requests += 1
                errors.append(str(e))
        
        # Create tasks for concurrent requests
        tasks = []
        for _ in range(concurrent_users):
            for _ in range(requests_per_user):
                tasks.append(make_request())
        
        # Execute all requests concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        total_requests = concurrent_users * requests_per_user
        
        # Calculate statistics
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = self._percentile(response_times, 95)
            p99_response_time = self._percentile(response_times, 99)
        else:
            avg_response_time = min_response_time = max_response_time = 0
            p95_response_time = p99_response_time = 0
        
        requests_per_second = total_requests / total_time if total_time > 0 else 0
        
        result = LoadTestResult(
            endpoint=endpoint,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            average_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            errors=errors[:10]  # Limit to first 10 errors
        )
        
        self.results.append(result)
        return result
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def print_results(self):
        """Print formatted test results."""
        print("\n" + "=" * 80)
        print("📊 LOAD TEST RESULTS")
        print("=" * 80)
        
        for result in self.results:
            print(f"\n🔗 Endpoint: {result.endpoint}")
            print(f"   Total Requests: {result.total_requests}")
            print(f"   Successful: {result.successful_requests} ({result.successful_requests/result.total_requests*100:.1f}%)")
            print(f"   Failed: {result.failed_requests} ({result.failed_requests/result.total_requests*100:.1f}%)")
            print(f"   Requests/sec: {result.requests_per_second:.2f}")
            print(f"   Avg Response Time: {result.average_response_time:.2f}ms")
            print(f"   Min Response Time: {result.min_response_time:.2f}ms")
            print(f"   Max Response Time: {result.max_response_time:.2f}ms")
            print(f"   95th Percentile: {result.p95_response_time:.2f}ms")
            print(f"   99th Percentile: {result.p99_response_time:.2f}ms")
            
            if result.errors:
                print(f"   Errors: {len(result.errors)} (showing first 3)")
                for error in result.errors[:3]:
                    print(f"     - {error}")
        
        # Summary
        print("\n" + "=" * 80)
        print("📈 SUMMARY")
        print("=" * 80)
        
        total_requests = sum(r.total_requests for r in self.results)
        total_successful = sum(r.successful_requests for r in self.results)
        total_failed = sum(r.failed_requests for r in self.results)
        
        print(f"Total Requests: {total_requests}")
        print(f"Success Rate: {total_successful/total_requests*100:.1f}%")
        print(f"Failure Rate: {total_failed/total_requests*100:.1f}%")
        
        # Performance analysis
        print("\n🎯 PERFORMANCE ANALYSIS:")
        for result in self.results:
            if result.average_response_time > 500:
                print(f"   ⚠️  {result.endpoint}: Average response time ({result.average_response_time:.0f}ms) exceeds 500ms budget")
            if result.p95_response_time > 1000:
                print(f"   ⚠️  {result.endpoint}: 95th percentile ({result.p95_response_time:.0f}ms) exceeds 1000ms")
            if result.requests_per_second < 10:
                print(f"   ⚠️  {result.endpoint}: Low throughput ({result.requests_per_second:.1f} req/s)")
    
    def check_performance_budgets(self) -> bool:
        """Check if performance meets budgets."""
        budgets_met = True
        
        for result in self.results:
            # Latency budget: <500ms average, <1000ms 95th percentile
            if result.average_response_time > 500:
                print(f"❌ {result.endpoint}: Average response time ({result.average_response_time:.0f}ms) exceeds 500ms budget")
                budgets_met = False
            
            if result.p95_response_time > 1000:
                print(f"❌ {result.endpoint}: 95th percentile ({result.p95_response_time:.0f}ms) exceeds 1000ms budget")
                budgets_met = False
            
            # Throughput budget: >10 req/s
            if result.requests_per_second < 10:
                print(f"❌ {result.endpoint}: Throughput ({result.requests_per_second:.1f} req/s) below 10 req/s budget")
                budgets_met = False
            
            # Error rate budget: <1%
            error_rate = result.failed_requests / result.total_requests * 100
            if error_rate > 1:
                print(f"❌ {result.endpoint}: Error rate ({error_rate:.1f}%) exceeds 1% budget")
                budgets_met = False
        
        return budgets_met

async def run_comprehensive_load_test():
    """Run comprehensive load tests on all endpoints."""
    async with LoadTester() as tester:
        print("🧪 Starting Comprehensive Load Test...")
        print("=" * 50)
        
        # Test core endpoints
        await tester.test_endpoint("/api/health", concurrent_users=20, requests_per_user=25)
        await tester.test_endpoint("/api/services", concurrent_users=15, requests_per_user=30)
        await tester.test_endpoint("/api/metrics", concurrent_users=15, requests_per_user=30)
        await tester.test_endpoint("/api/activity", concurrent_users=10, requests_per_user=20)
        
        # Test AI Assistant endpoint
        ai_payload = {
            "message": "Test message for load testing",
            "context": {"conversation_history": []}
        }
        await tester.test_endpoint("/api/ai/chat", method="POST", 
                                 concurrent_users=5, requests_per_user=10,
                                 payload=ai_payload)
        
        # Test email endpoints
        await tester.test_endpoint("/api/email/providers", concurrent_users=10, requests_per_user=15)
        
        # Print results
        tester.print_results()
        
        # Check performance budgets
        print("\n🎯 PERFORMANCE BUDGET CHECK:")
        budgets_met = tester.check_performance_budgets()
        
        if budgets_met:
            print("✅ All performance budgets met!")
        else:
            print("❌ Some performance budgets not met. Consider optimization.")
        
        return budgets_met

async def run_stress_test():
    """Run stress test with high load."""
    async with LoadTester() as tester:
        print("🔥 Starting Stress Test...")
        print("=" * 50)
        
        # High load test
        await tester.test_endpoint("/api/health", concurrent_users=50, requests_per_user=100)
        await tester.test_endpoint("/api/services", concurrent_users=30, requests_per_user=50)
        
        tester.print_results()
        return tester.check_performance_budgets()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Fikiri Solutions Load Testing")
    parser.add_argument("--test-type", choices=["comprehensive", "stress"], 
                       default="comprehensive", help="Type of test to run")
    parser.add_argument("--base-url", default="http://localhost:8081", 
                       help="Base URL for testing")
    
    args = parser.parse_args()
    
    if args.test_type == "comprehensive":
        success = asyncio.run(run_comprehensive_load_test())
    elif args.test_type == "stress":
        success = asyncio.run(run_stress_test())
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
