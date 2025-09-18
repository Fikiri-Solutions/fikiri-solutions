#!/usr/bin/env python3
"""
Fikiri Solutions - Structured Logging & Monitoring
JSON-based logging with service monitoring and error tracking.
"""

import json
import logging
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
import traceback

class StructuredLogger:
    """Structured JSON logger for Fikiri Solutions."""
    
    def __init__(self, name: str = "fikiri", log_level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create console handler with JSON formatting
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(console_handler)
        
        # Create file handler if LOG_FILE is set
        log_file = os.getenv('LOG_FILE')
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(JSONFormatter())
            self.logger.addHandler(file_handler)
    
    def log(self, level: str, message: str, **kwargs):
        """Log a structured message."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level.upper(),
            'message': message,
            'service': 'fikiri-backend',
            **kwargs
        }
        
        getattr(self.logger, level.lower())(json.dumps(log_data))
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.log('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.log('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.log('ERROR', message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.log('DEBUG', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.log('CRITICAL', message, **kwargs)

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        """Format log record as JSON."""
        try:
            # If record.msg is already JSON, return it
            if isinstance(record.msg, str) and record.msg.startswith('{'):
                return record.msg
        except:
            pass
        
        # Create structured log entry
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'service': 'fikiri-backend',
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_entry)

class ServiceMonitor:
    """Monitor service health and performance."""
    
    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.metrics = {
            'requests_total': 0,
            'requests_successful': 0,
            'requests_failed': 0,
            'response_times': [],
            'errors_by_service': {},
            'last_health_check': None
        }
    
    def track_request(self, service: str, endpoint: str, method: str, 
                     response_time: float, status_code: int, error: Optional[str] = None):
        """Track API request metrics."""
        self.metrics['requests_total'] += 1
        
        if 200 <= status_code < 400:
            self.metrics['requests_successful'] += 1
        else:
            self.metrics['requests_failed'] += 1
        
        self.metrics['response_times'].append(response_time)
        
        # Keep only last 1000 response times
        if len(self.metrics['response_times']) > 1000:
            self.metrics['response_times'] = self.metrics['response_times'][-1000:]
        
        # Track errors by service
        if error:
            if service not in self.metrics['errors_by_service']:
                self.metrics['errors_by_service'][service] = 0
            self.metrics['errors_by_service'][service] += 1
        
        # Log the request
        self.logger.info(
            f"API Request: {method} {endpoint}",
            service=service,
            endpoint=endpoint,
            method=method,
            response_time_ms=round(response_time * 1000, 2),
            status_code=status_code,
            error=error
        )
    
    def track_service_health(self, service: str, is_healthy: bool, 
                           response_time: Optional[float] = None, error: Optional[str] = None):
        """Track service health check."""
        self.metrics['last_health_check'] = time.time()
        
        self.logger.info(
            f"Service Health Check: {service}",
            service=service,
            is_healthy=is_healthy,
            response_time_ms=round(response_time * 1000, 2) if response_time else None,
            error=error
        )
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        total_requests = self.metrics['requests_total']
        successful_requests = self.metrics['requests_successful']
        failed_requests = self.metrics['requests_failed']
        
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        error_rate = (failed_requests / total_requests * 100) if total_requests > 0 else 0
        
        response_times = self.metrics['response_times']
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate_percent': round(success_rate, 2),
            'error_rate_percent': round(error_rate, 2),
            'average_response_time_ms': round(avg_response_time * 1000, 2),
            'errors_by_service': self.metrics['errors_by_service'],
            'last_health_check': self.metrics['last_health_check']
        }
    
    def log_metrics_summary(self):
        """Log metrics summary."""
        summary = self.get_metrics_summary()
        self.logger.info("Service Metrics Summary", **summary)

# Global instances
logger = StructuredLogger()
monitor = ServiceMonitor(logger)

def log_api_request(endpoint: str, method: str, status_code: int, 
                   response_time: float, user_agent: Optional[str] = None):
    """Log API request with structured data."""
    logger.info(
        f"API Request: {method} {endpoint}",
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        response_time_ms=round(response_time * 1000, 2),
        user_agent=user_agent
    )

def log_service_action(service: str, action: str, success: bool, 
                     details: Optional[Dict[str, Any]] = None):
    """Log service action with structured data."""
    logger.info(
        f"Service Action: {service}.{action}",
        service=service,
        action=action,
        success=success,
        details=details or {}
    )

def log_security_event(event_type: str, severity: str, details: Dict[str, Any]):
    """Log security event with structured data."""
    logger.warning(
        f"Security Event: {event_type}",
        event_type=event_type,
        severity=severity,
        **details
    )

def log_performance_metric(metric_name: str, value: float, unit: str = "ms"):
    """Log performance metric."""
    logger.info(
        f"Performance Metric: {metric_name}",
        metric_name=metric_name,
        value=value,
        unit=unit
    )

def monitor_endpoint(endpoint_name: str):
    """Decorator to monitor endpoint performance."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                response_time = time.time() - start_time
                
                monitor.track_request(
                    service='api',
                    endpoint=endpoint_name,
                    method='GET',  # Could be enhanced to detect method
                    response_time=response_time,
                    status_code=200
                )
                
                return result
            except Exception as e:
                response_time = time.time() - start_time
                
                monitor.track_request(
                    service='api',
                    endpoint=endpoint_name,
                    method='GET',
                    response_time=response_time,
                    status_code=500,
                    error=str(e)
                )
                
                logger.error(
                    f"Endpoint Error: {endpoint_name}",
                    endpoint=endpoint_name,
                    error=str(e),
                    traceback=traceback.format_exc()
                )
                
                raise
        return wrapper
    return decorator

def log_startup():
    """Log application startup."""
    logger.info(
        "Fikiri Solutions Backend Starting",
        version="1.0.0",
        environment=os.getenv('ENVIRONMENT', 'development'),
        log_level=os.getenv('LOG_LEVEL', 'INFO')
    )

def log_shutdown():
    """Log application shutdown."""
    logger.info("Fikiri Solutions Backend Shutting Down")
    monitor.log_metrics_summary()

# Error tracking
class ErrorTracker:
    """Track and categorize errors."""
    
    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.error_counts = {}
        self.error_patterns = {}
    
    def track_error(self, error_type: str, service: str, error_message: str):
        """Track error occurrence."""
        key = f"{service}:{error_type}"
        
        if key not in self.error_counts:
            self.error_counts[key] = 0
        self.error_counts[key] += 1
        
        # Track error patterns
        if error_type not in self.error_patterns:
            self.error_patterns[error_type] = []
        self.error_patterns[error_type].append({
            'service': service,
            'message': error_message,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Log the error
        self.logger.error(
            f"Error Tracked: {error_type}",
            error_type=error_type,
            service=service,
            error_message=error_message,
            count=self.error_counts[key]
        )
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get error summary."""
        return {
            'error_counts': self.error_counts,
            'total_errors': sum(self.error_counts.values()),
            'unique_error_types': len(self.error_counts),
            'error_patterns': self.error_patterns
        }

# Global error tracker
error_tracker = ErrorTracker(logger)

# Global performance monitor (using the main performance_monitor from performance_monitor.py)
# Import the main performance monitor to avoid duplication
from core.performance_monitor import performance_monitor

if __name__ == "__main__":
    # Test the logging system
    log_startup()
    
    logger.info("Test info message", test_data="example")
    logger.warning("Test warning message", warning_code="TEST_WARN")
    logger.error("Test error message", error_code="TEST_ERROR")
    
    # Test monitoring
    monitor.track_request('test', '/api/test', 'GET', 0.1, 200)
    monitor.track_service_health('test_service', True, 0.05)
    
    # Test error tracking
    error_tracker.track_error('TestError', 'test_service', 'Test error message')
    
    # Test performance monitoring
    performance_monitor.track_latency('api_request', 150.5)
    performance_monitor.track_throughput('api_requests', 25.3)
    performance_monitor.track_memory_usage(128.7)
    
    monitor.log_metrics_summary()
    log_shutdown()
