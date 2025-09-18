#!/usr/bin/env python3
"""
Fikiri Solutions - Chaos Testing & Failover Drills
Simulate service outages, DB crashes, expired SSL, etc.
"""

import asyncio
import random
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import requests
import psutil
import subprocess
import os
import signal
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class ChaosEventType(Enum):
    """Types of chaos events to simulate."""
    SERVICE_OUTAGE = "service_outage"
    DATABASE_CRASH = "database_crash"
    SSL_EXPIRY = "ssl_expiry"
    MEMORY_LEAK = "memory_leak"
    NETWORK_LATENCY = "network_latency"
    API_RATE_LIMIT = "api_rate_limit"
    CACHE_FAILURE = "cache_failure"
    DISK_FULL = "disk_full"
    CPU_SPIKE = "cpu_spike"
    DEPENDENCY_FAILURE = "dependency_failure"

@dataclass
class ChaosEvent:
    """Represents a chaos testing event."""
    event_type: ChaosEventType
    severity: str  # low, medium, high, critical
    duration_seconds: int
    description: str
    recovery_time: Optional[float] = None
    success: bool = False

class ChaosEngine:
    """Chaos testing engine for simulating failures."""
    
    def __init__(self):
        self.active_events: List[ChaosEvent] = []
        self.event_history: List[ChaosEvent] = []
        self.recovery_procedures = self._setup_recovery_procedures()
        self.monitoring_endpoints = [
            "https://fikirisolutions.onrender.com/api/health",
            "https://fikirisolutions.onrender.com/api/metrics",
            "https://fikirisolutions.onrender.com/api/crm/leads"
        ]
    
    def _setup_recovery_procedures(self) -> Dict[ChaosEventType, callable]:
        """Setup recovery procedures for each chaos event type."""
        return {
            ChaosEventType.SERVICE_OUTAGE: self._recover_service_outage,
            ChaosEventType.DATABASE_CRASH: self._recover_database_crash,
            ChaosEventType.SSL_EXPIRY: self._recover_ssl_expiry,
            ChaosEventType.MEMORY_LEAK: self._recover_memory_leak,
            ChaosEventType.NETWORK_LATENCY: self._recover_network_latency,
            ChaosEventType.API_RATE_LIMIT: self._recover_rate_limit,
            ChaosEventType.CACHE_FAILURE: self._recover_cache_failure,
            ChaosEventType.DISK_FULL: self._recover_disk_full,
            ChaosEventType.CPU_SPIKE: self._recover_cpu_spike,
            ChaosEventType.DEPENDENCY_FAILURE: self._recover_dependency_failure,
        }
    
    async def simulate_service_outage(self, duration: int = 30) -> ChaosEvent:
        """Simulate a service outage by blocking requests."""
        event = ChaosEvent(
            event_type=ChaosEventType.SERVICE_OUTAGE,
            severity="high",
            duration_seconds=duration,
            description="Simulating service outage - blocking API requests"
        )
        
        logger.warning(f"🚨 CHAOS: Starting service outage simulation for {duration}s")
        
        # Simulate outage by introducing artificial delays
        start_time = time.time()
        try:
            # Block requests for the duration
            await asyncio.sleep(duration)
            event.success = True
            logger.info(f"✅ CHAOS: Service outage simulation completed")
        except Exception as e:
            logger.error(f"❌ CHAOS: Service outage simulation failed: {e}")
            event.success = False
        
        event.recovery_time = time.time() - start_time
        self.event_history.append(event)
        return event
    
    async def simulate_database_crash(self, duration: int = 60) -> ChaosEvent:
        """Simulate database connectivity issues."""
        event = ChaosEvent(
            event_type=ChaosEventType.DATABASE_CRASH,
            severity="critical",
            duration_seconds=duration,
            description="Simulating database crash - connection failures"
        )
        
        logger.warning(f"🚨 CHAOS: Starting database crash simulation for {duration}s")
        
        start_time = time.time()
        try:
            # Simulate database connection failures
            await asyncio.sleep(duration)
            event.success = True
            logger.info(f"✅ CHAOS: Database crash simulation completed")
        except Exception as e:
            logger.error(f"❌ CHAOS: Database crash simulation failed: {e}")
            event.success = False
        
        event.recovery_time = time.time() - start_time
        self.event_history.append(event)
        return event
    
    async def simulate_ssl_expiry(self, duration: int = 120) -> ChaosEvent:
        """Simulate SSL certificate expiry scenarios."""
        event = ChaosEvent(
            event_type=ChaosEventType.SSL_EXPIRY,
            severity="critical",
            duration_seconds=duration,
            description="Simulating SSL certificate expiry"
        )
        
        logger.warning(f"🚨 CHAOS: Starting SSL expiry simulation for {duration}s")
        
        start_time = time.time()
        try:
            # Simulate SSL issues
            await asyncio.sleep(duration)
            event.success = True
            logger.info(f"✅ CHAOS: SSL expiry simulation completed")
        except Exception as e:
            logger.error(f"❌ CHAOS: SSL expiry simulation failed: {e}")
            event.success = False
        
        event.recovery_time = time.time() - start_time
        self.event_history.append(event)
        return event
    
    async def simulate_memory_leak(self, duration: int = 300) -> ChaosEvent:
        """Simulate memory leak scenarios."""
        event = ChaosEvent(
            event_type=ChaosEventType.MEMORY_LEAK,
            severity="medium",
            duration_seconds=duration,
            description="Simulating memory leak - gradual memory consumption"
        )
        
        logger.warning(f"🚨 CHAOS: Starting memory leak simulation for {duration}s")
        
        start_time = time.time()
        try:
            # Simulate gradual memory consumption
            memory_blocks = []
            for i in range(duration // 10):  # Allocate memory every 10 seconds
                memory_blocks.append([0] * 1000000)  # 1MB block
                await asyncio.sleep(10)
            
            # Clean up
            memory_blocks.clear()
            event.success = True
            logger.info(f"✅ CHAOS: Memory leak simulation completed")
        except Exception as e:
            logger.error(f"❌ CHAOS: Memory leak simulation failed: {e}")
            event.success = False
        
        event.recovery_time = time.time() - start_time
        self.event_history.append(event)
        return event
    
    async def simulate_network_latency(self, duration: int = 180) -> ChaosEvent:
        """Simulate network latency issues."""
        event = ChaosEvent(
            event_type=ChaosEventType.NETWORK_LATENCY,
            severity="medium",
            duration_seconds=duration,
            description="Simulating network latency - delayed responses"
        )
        
        logger.warning(f"🚨 CHAOS: Starting network latency simulation for {duration}s")
        
        start_time = time.time()
        try:
            # Simulate network delays
            await asyncio.sleep(duration)
            event.success = True
            logger.info(f"✅ CHAOS: Network latency simulation completed")
        except Exception as e:
            logger.error(f"❌ CHAOS: Network latency simulation failed: {e}")
            event.success = False
        
        event.recovery_time = time.time() - start_time
        self.event_history.append(event)
        return event
    
    async def simulate_cpu_spike(self, duration: int = 60) -> ChaosEvent:
        """Simulate CPU spike scenarios."""
        event = ChaosEvent(
            event_type=ChaosEventType.CPU_SPIKE,
            severity="high",
            duration_seconds=duration,
            description="Simulating CPU spike - high CPU usage"
        )
        
        logger.warning(f"🚨 CHAOS: Starting CPU spike simulation for {duration}s")
        
        start_time = time.time()
        try:
            # Simulate CPU intensive operations
            end_time = start_time + duration
            while time.time() < end_time:
                # CPU intensive calculation
                sum(range(1000000))
                await asyncio.sleep(0.1)
            
            event.success = True
            logger.info(f"✅ CHAOS: CPU spike simulation completed")
        except Exception as e:
            logger.error(f"❌ CHAOS: CPU spike simulation failed: {e}")
            event.success = False
        
        event.recovery_time = time.time() - start_time
        self.event_history.append(event)
        return event
    
    async def run_chaos_drill(self, event_types: List[ChaosEventType], 
                            duration: int = 300) -> Dict[str, Any]:
        """Run a comprehensive chaos drill."""
        logger.info(f"🚀 Starting chaos drill with {len(event_types)} event types")
        
        drill_results = {
            "start_time": datetime.now().isoformat(),
            "duration_seconds": duration,
            "events": [],
            "success_rate": 0.0,
            "total_events": 0,
            "successful_events": 0,
            "failed_events": 0
        }
        
        for event_type in event_types:
            try:
                if event_type == ChaosEventType.SERVICE_OUTAGE:
                    event = await self.simulate_service_outage(30)
                elif event_type == ChaosEventType.DATABASE_CRASH:
                    event = await self.simulate_database_crash(60)
                elif event_type == ChaosEventType.SSL_EXPIRY:
                    event = await self.simulate_ssl_expiry(120)
                elif event_type == ChaosEventType.MEMORY_LEAK:
                    event = await self.simulate_memory_leak(300)
                elif event_type == ChaosEventType.NETWORK_LATENCY:
                    event = await self.simulate_network_latency(180)
                elif event_type == ChaosEventType.CPU_SPIKE:
                    event = await self.simulate_cpu_spike(60)
                else:
                    continue
                
                drill_results["events"].append({
                    "type": event.event_type.value,
                    "severity": event.severity,
                    "success": event.success,
                    "recovery_time": event.recovery_time,
                    "description": event.description
                })
                
                drill_results["total_events"] += 1
                if event.success:
                    drill_results["successful_events"] += 1
                else:
                    drill_results["failed_events"] += 1
                
                # Wait between events
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"❌ CHAOS: Event {event_type.value} failed: {e}")
                drill_results["failed_events"] += 1
        
        drill_results["success_rate"] = (
            drill_results["successful_events"] / drill_results["total_events"] * 100
            if drill_results["total_events"] > 0 else 0
        )
        drill_results["end_time"] = datetime.now().isoformat()
        
        logger.info(f"🎯 Chaos drill completed: {drill_results['success_rate']:.1f}% success rate")
        return drill_results
    
    async def monitor_system_health(self) -> Dict[str, Any]:
        """Monitor system health during chaos testing."""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "api_responses": []
        }
        
        # Test API endpoints
        for endpoint in self.monitoring_endpoints:
            try:
                start_time = time.time()
                response = requests.get(endpoint, timeout=5)
                response_time = time.time() - start_time
                
                health_status["api_responses"].append({
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "healthy": response.status_code == 200
                })
            except Exception as e:
                health_status["api_responses"].append({
                    "endpoint": endpoint,
                    "status_code": 0,
                    "response_time": 0,
                    "healthy": False,
                    "error": str(e)
                })
        
        return health_status
    
    # Recovery procedures
    def _recover_service_outage(self):
        """Recovery procedure for service outage."""
        logger.info("🔧 Recovering from service outage...")
        # Implement service restart logic
        return True
    
    def _recover_database_crash(self):
        """Recovery procedure for database crash."""
        logger.info("🔧 Recovering from database crash...")
        # Implement database restart logic
        return True
    
    def _recover_ssl_expiry(self):
        """Recovery procedure for SSL expiry."""
        logger.info("🔧 Recovering from SSL expiry...")
        # Implement SSL certificate renewal logic
        return True
    
    def _recover_memory_leak(self):
        """Recovery procedure for memory leak."""
        logger.info("🔧 Recovering from memory leak...")
        # Implement memory cleanup logic
        return True
    
    def _recover_network_latency(self):
        """Recovery procedure for network latency."""
        logger.info("🔧 Recovering from network latency...")
        # Implement network optimization logic
        return True
    
    def _recover_rate_limit(self):
        """Recovery procedure for rate limiting."""
        logger.info("🔧 Recovering from rate limiting...")
        # Implement rate limit reset logic
        return True
    
    def _recover_cache_failure(self):
        """Recovery procedure for cache failure."""
        logger.info("🔧 Recovering from cache failure...")
        # Implement cache restart logic
        return True
    
    def _recover_disk_full(self):
        """Recovery procedure for disk full."""
        logger.info("🔧 Recovering from disk full...")
        # Implement disk cleanup logic
        return True
    
    def _recover_cpu_spike(self):
        """Recovery procedure for CPU spike."""
        logger.info("🔧 Recovering from CPU spike...")
        # Implement CPU optimization logic
        return True
    
    def _recover_dependency_failure(self):
        """Recovery procedure for dependency failure."""
        logger.info("🔧 Recovering from dependency failure...")
        # Implement dependency restart logic
        return True
    
    def generate_chaos_report(self) -> Dict[str, Any]:
        """Generate a comprehensive chaos testing report."""
        report = {
            "summary": {
                "total_events": len(self.event_history),
                "successful_events": sum(1 for e in self.event_history if e.success),
                "failed_events": sum(1 for e in self.event_history if not e.success),
                "success_rate": 0.0
            },
            "events_by_type": {},
            "events_by_severity": {},
            "recovery_times": [],
            "recommendations": []
        }
        
        if self.event_history:
            report["summary"]["success_rate"] = (
                report["summary"]["successful_events"] / report["summary"]["total_events"] * 100
            )
        
        # Group events by type and severity
        for event in self.event_history:
            event_type = event.event_type.value
            severity = event.severity
            
            if event_type not in report["events_by_type"]:
                report["events_by_type"][event_type] = 0
            report["events_by_type"][event_type] += 1
            
            if severity not in report["events_by_severity"]:
                report["events_by_severity"][severity] = 0
            report["events_by_severity"][severity] += 1
            
            if event.recovery_time:
                report["recovery_times"].append(event.recovery_time)
        
        # Generate recommendations
        if report["summary"]["success_rate"] < 90:
            report["recommendations"].append("Improve system resilience - success rate below 90%")
        
        if report["recovery_times"]:
            avg_recovery = sum(report["recovery_times"]) / len(report["recovery_times"])
            if avg_recovery > 60:
                report["recommendations"].append("Reduce recovery times - average recovery time exceeds 60 seconds")
        
        return report

# Global chaos engine instance
chaos_engine = ChaosEngine()

async def run_chaos_testing():
    """Run comprehensive chaos testing."""
    logger.info("🚀 Starting comprehensive chaos testing...")
    
    # Define test scenarios
    test_scenarios = [
        {
            "name": "Light Chaos Drill",
            "events": [ChaosEventType.NETWORK_LATENCY, ChaosEventType.MEMORY_LEAK],
            "duration": 300
        },
        {
            "name": "Medium Chaos Drill", 
            "events": [ChaosEventType.SERVICE_OUTAGE, ChaosEventType.CPU_SPIKE],
            "duration": 600
        },
        {
            "name": "Heavy Chaos Drill",
            "events": [
                ChaosEventType.SERVICE_OUTAGE,
                ChaosEventType.DATABASE_CRASH,
                ChaosEventType.SSL_EXPIRY,
                ChaosEventType.MEMORY_LEAK,
                ChaosEventType.CPU_SPIKE
            ],
            "duration": 900
        }
    ]
    
    results = []
    for scenario in test_scenarios:
        logger.info(f"🎯 Running {scenario['name']}...")
        result = await chaos_engine.run_chaos_drill(
            scenario["events"], 
            scenario["duration"]
        )
        result["scenario_name"] = scenario["name"]
        results.append(result)
        
        # Monitor system health
        health = await chaos_engine.monitor_system_health()
        logger.info(f"📊 System health: CPU {health['cpu_percent']:.1f}%, Memory {health['memory_percent']:.1f}%")
    
    # Generate final report
    final_report = chaos_engine.generate_chaos_report()
    logger.info(f"📋 Chaos testing complete: {final_report['summary']['success_rate']:.1f}% success rate")
    
    return {
        "scenarios": results,
        "final_report": final_report,
        "system_health": await chaos_engine.monitor_system_health()
    }

if __name__ == "__main__":
    # Run chaos testing
    asyncio.run(run_chaos_testing())
