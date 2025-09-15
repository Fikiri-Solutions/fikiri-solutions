#!/usr/bin/env python3
"""
Fikiri Solutions - Performance Monitoring & Error Handling
Latency budgets, error surfacing, and retry logic implementation.
"""

import time
import functools
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import asyncio
import aiohttp
from contextlib import asynccontextmanager

class PerformanceBudget(Enum):
    """Performance budget thresholds."""
    API_RESPONSE_MS = 500
    API_P95_RESPONSE_MS = 1000
    DATABASE_QUERY_MS = 200
    AI_RESPONSE_MS = 2000
    EMAIL_PROCESSING_MS = 1000

@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""
    operation: str
    start_time: float
    end_time: float
    duration_ms: float
    success: bool
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    def __init__(self):
        self.metrics: list[PerformanceMetrics] = []
        self.budgets = PerformanceBudget
        self.logger = logging.getLogger(__name__)
    
    def track_operation(self, operation: str, duration_ms: float, 
                       success: bool, error: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None):
        """Track operation performance."""
        metric = PerformanceMetrics(
            operation=operation,
            start_time=time.time() - (duration_ms / 1000),
            end_time=time.time(),
            duration_ms=duration_ms,
            success=success,
            error=error,
            metadata=metadata
        )
        
        self.metrics.append(metric)
        
        # Log performance
        if success:
            self.logger.info(f"Operation {operation} completed in {duration_ms:.2f}ms")
        else:
            self.logger.error(f"Operation {operation} failed after {duration_ms:.2f}ms: {error}")
        
        # Check budget
        self._check_budget(metric)
    
    def _check_budget(self, metric: PerformanceMetrics):
        """Check if operation meets performance budget."""
        budget_map = {
            'api_request': self.budgets.API_RESPONSE_MS.value,
            'database_query': self.budgets.DATABASE_QUERY_MS.value,
            'ai_response': self.budgets.AI_RESPONSE_MS.value,
            'email_processing': self.budgets.EMAIL_PROCESSING_MS.value
        }
        
        budget = budget_map.get(metric.operation, self.budgets.API_RESPONSE_MS.value)
        
        if metric.duration_ms > budget:
            self.logger.warning(
                f"Performance budget exceeded: {metric.operation} "
                f"took {metric.duration_ms:.2f}ms (budget: {budget}ms)"
            )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if not self.metrics:
            return {}
        
        successful_metrics = [m for m in self.metrics if m.success]
        failed_metrics = [m for m in self.metrics if not m.success]
        
        return {
            'total_operations': len(self.metrics),
            'successful_operations': len(successful_metrics),
            'failed_operations': len(failed_metrics),
            'success_rate': len(successful_metrics) / len(self.metrics) * 100,
            'average_duration_ms': sum(m.duration_ms for m in successful_metrics) / len(successful_metrics) if successful_metrics else 0,
            'max_duration_ms': max(m.duration_ms for m in self.metrics),
            'min_duration_ms': min(m.duration_ms for m in self.metrics),
            'budget_violations': len([m for m in self.metrics if self._exceeds_budget(m)])
        }
    
    def _exceeds_budget(self, metric: PerformanceMetrics) -> bool:
        """Check if metric exceeds budget."""
        budget_map = {
            'api_request': self.budgets.API_RESPONSE_MS.value,
            'database_query': self.budgets.DATABASE_QUERY_MS.value,
            'ai_response': self.budgets.AI_RESPONSE_MS.value,
            'email_processing': self.budgets.EMAIL_PROCESSING_MS.value
        }
        
        budget = budget_map.get(metric.operation, self.budgets.API_RESPONSE_MS.value)
        return metric.duration_ms > budget

# Global performance monitor
performance_monitor = PerformanceMonitor()

def monitor_performance(operation_name: str):
    """Decorator to monitor function performance."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                
                performance_monitor.track_operation(
                    operation=operation_name,
                    duration_ms=duration_ms,
                    success=success,
                    error=error
                )
        
        return wrapper
    return decorator

class ErrorHandler:
    """Centralized error handling and surfacing."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_counts: Dict[str, int] = {}
    
    def handle_error(self, error: Exception, context: str, 
                    user_message: Optional[str] = None) -> Dict[str, Any]:
        """Handle and surface errors with user-friendly messages."""
        error_type = type(error).__name__
        error_key = f"{context}:{error_type}"
        
        # Track error frequency
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Log error details
        self.logger.error(
            f"Error in {context}: {error_type}",
            extra={
                'error_type': error_type,
                'error_message': str(error),
                'context': context,
                'error_count': self.error_counts[error_key]
            }
        )
        
        # Return user-friendly error response
        return {
            'error': True,
            'message': user_message or self._get_user_friendly_message(error_type),
            'error_type': error_type,
            'context': context,
            'timestamp': time.time()
        }
    
    def _get_user_friendly_message(self, error_type: str) -> str:
        """Get user-friendly error message."""
        friendly_messages = {
            'ConnectionError': 'Unable to connect to the service. Please try again.',
            'TimeoutError': 'The request timed out. Please try again.',
            'ValueError': 'Invalid input provided. Please check your data.',
            'KeyError': 'Required information is missing.',
            'PermissionError': 'You do not have permission to perform this action.',
            'FileNotFoundError': 'The requested resource was not found.',
            'ImportError': 'A required service is not available.',
            'AttributeError': 'An internal error occurred. Please try again.'
        }
        
        return friendly_messages.get(error_type, 'An unexpected error occurred. Please try again.')

# Global error handler
error_handler = ErrorHandler()

class RetryConfig:
    """Retry configuration."""
    def __init__(self, max_retries: int = 2, base_delay: float = 1.0, 
                 max_delay: float = 10.0, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

def retry_with_backoff(config: RetryConfig = None):
    """Decorator for retry logic with exponential backoff."""
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == config.max_retries:
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.backoff_factor ** attempt),
                        config.max_delay
                    )
                    
                    time.sleep(delay)
            
            # Re-raise the last exception
            raise last_exception
        
        return wrapper
    return decorator

class APIClient:
    """HTTP client with performance monitoring and error handling."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.session = None
        self.logger = logging.getLogger(__name__)
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    @retry_with_backoff(RetryConfig(max_retries=2, base_delay=1.0))
    async def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make GET request with monitoring."""
        start_time = time.time()
        success = True
        error = None
        
        try:
            url = f"{self.base_url}{endpoint}"
            async with self.session.get(url, **kwargs) as response:
                data = await response.json()
                
                if response.status >= 400:
                    success = False
                    error = f"HTTP {response.status}: {data.get('message', 'Unknown error')}"
                
                return data
                
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            performance_monitor.track_operation(
                operation='api_request',
                duration_ms=duration_ms,
                success=success,
                error=error,
                metadata={'endpoint': endpoint, 'method': 'GET'}
            )
    
    @retry_with_backoff(RetryConfig(max_retries=2, base_delay=1.0))
    async def post(self, endpoint: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Make POST request with monitoring."""
        start_time = time.time()
        success = True
        error = None
        
        try:
            url = f"{self.base_url}{endpoint}"
            async with self.session.post(url, json=data, **kwargs) as response:
                response_data = await response.json()
                
                if response.status >= 400:
                    success = False
                    error = f"HTTP {response.status}: {response_data.get('message', 'Unknown error')}"
                
                return response_data
                
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            performance_monitor.track_operation(
                operation='api_request',
                duration_ms=duration_ms,
                success=success,
                error=error,
                metadata={'endpoint': endpoint, 'method': 'POST'}
            )

class DatabaseMonitor:
    """Monitor database query performance."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @monitor_performance('database_query')
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None):
        """Execute database query with monitoring."""
        # This would be implemented with actual database connection
        # For now, simulate query execution
        time.sleep(0.1)  # Simulate query time
        return {"rows": [], "count": 0}

class AIMonitor:
    """Monitor AI service performance."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @monitor_performance('ai_response')
    def generate_response(self, prompt: str) -> str:
        """Generate AI response with monitoring."""
        # This would be implemented with actual AI service
        # For now, simulate AI response
        time.sleep(0.5)  # Simulate AI processing time
        return "AI response generated"

# Example usage
async def example_api_call():
    """Example of monitored API call."""
    async with APIClient("http://localhost:8081") as client:
        try:
            response = await client.get("/api/health")
            return response
        except Exception as e:
            return error_handler.handle_error(e, "api_call", "Failed to check system health")

def example_database_query():
    """Example of monitored database query."""
    db_monitor = DatabaseMonitor()
    try:
        result = db_monitor.execute_query("SELECT * FROM users WHERE active = %s", {"active": True})
        return result
    except Exception as e:
        return error_handler.handle_error(e, "database_query", "Failed to fetch user data")

def example_ai_processing():
    """Example of monitored AI processing."""
    ai_monitor = AIMonitor()
    try:
        response = ai_monitor.generate_response("Generate a response for this email")
        return response
    except Exception as e:
        return error_handler.handle_error(e, "ai_processing", "Failed to generate AI response")

if __name__ == "__main__":
    # Test the monitoring system
    logging.basicConfig(level=logging.INFO)
    
    print("🧪 Testing Performance Monitoring...")
    
    # Test database query
    example_database_query()
    
    # Test AI processing
    example_ai_processing()
    
    # Test async API call
    asyncio.run(example_api_call())
    
    # Print performance summary
    summary = performance_monitor.get_summary()
    print(f"\n📊 Performance Summary: {summary}")
