#!/usr/bin/env python3
"""
Fikiri Solutions - Enterprise Logging System
Production-ready logging with structured output and monitoring.
"""

import logging
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

class FikiriLogger:
    """Enterprise-grade logging system for Fikiri Solutions."""
    
    def __init__(self, name: str = "fikiri", log_level: str = "INFO"):
        """Initialize the logger with enterprise features."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Create logs directory
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        
        # Setup formatters
        self.json_formatter = JsonFormatter()
        self.console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Setup handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup file and console handlers."""
        # File handler for JSON logs
        file_handler = logging.FileHandler(
            self.logs_dir / f"fikiri_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setFormatter(self.json_formatter)
        
        # Console handler for human-readable logs
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self.console_formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_service_action(self, service: str, action: str, 
                          status: str, details: Optional[Dict] = None):
        """Log service actions with structured data."""
        log_data = {
            "service": service,
            "action": action,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        if status == "success":
            self.logger.info(f"Service {service} {action} completed", extra=log_data)
        elif status == "error":
            self.logger.error(f"Service {service} {action} failed", extra=log_data)
        else:
            self.logger.warning(f"Service {service} {action} {status}", extra=log_data)
    
    def log_api_request(self, endpoint: str, method: str, 
                       status_code: int, response_time: float,
                       user_agent: Optional[str] = None):
        """Log API requests with performance metrics."""
        log_data = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time_ms": response_time * 1000,
            "user_agent": user_agent,
            "timestamp": datetime.now().isoformat()
        }
        
        if status_code < 400:
            self.logger.info(f"API {method} {endpoint} - {status_code}", extra=log_data)
        else:
            self.logger.warning(f"API {method} {endpoint} - {status_code}", extra=log_data)
    
    def log_security_event(self, event_type: str, severity: str, 
                          details: Dict[str, Any]):
        """Log security events with high priority."""
        log_data = {
            "event_type": event_type,
            "severity": severity,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        if severity == "critical":
            self.logger.critical(f"Security event: {event_type}", extra=log_data)
        elif severity == "high":
            self.logger.error(f"Security event: {event_type}", extra=log_data)
        else:
            self.logger.warning(f"Security event: {event_type}", extra=log_data)
    
    def log_performance_metric(self, metric_name: str, value: float, 
                              unit: str = "ms", tags: Optional[Dict] = None):
        """Log performance metrics for monitoring."""
        log_data = {
            "metric_name": metric_name,
            "value": value,
            "unit": unit,
            "tags": tags or {},
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(f"Metric: {metric_name}={value}{unit}", extra=log_data)

class JsonFormatter(logging.Formatter):
    """Custom formatter for structured JSON logs."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, 'service'):
            log_entry['service'] = record.service
        if hasattr(record, 'action'):
            log_entry['action'] = record.action
        if hasattr(record, 'status'):
            log_entry['status'] = record.status
        if hasattr(record, 'details'):
            log_entry['details'] = record.details
        if hasattr(record, 'endpoint'):
            log_entry['endpoint'] = record.endpoint
        if hasattr(record, 'method'):
            log_entry['method'] = record.method
        if hasattr(record, 'status_code'):
            log_entry['status_code'] = record.status_code
        if hasattr(record, 'response_time_ms'):
            log_entry['response_time_ms'] = record.response_time_ms
        
        return json.dumps(log_entry)

# Global logger instance
fikiri_logger = FikiriLogger()

def get_logger(name: str = "fikiri") -> FikiriLogger:
    """Get a logger instance."""
    return FikiriLogger(name)

# Convenience functions
def log_service_action(service: str, action: str, status: str, details: Optional[Dict] = None):
    """Log service action."""
    fikiri_logger.log_service_action(service, action, status, details)

def log_api_request(endpoint: str, method: str, status_code: int, 
                   response_time: float, user_agent: Optional[str] = None):
    """Log API request."""
    fikiri_logger.log_api_request(endpoint, method, status_code, response_time, user_agent)

def log_security_event(event_type: str, severity: str, details: Dict[str, Any]):
    """Log security event."""
    fikiri_logger.log_security_event(event_type, severity, details)

def log_performance_metric(metric_name: str, value: float, unit: str = "ms", tags: Optional[Dict] = None):
    """Log performance metric."""
    fikiri_logger.log_performance_metric(metric_name, value, unit, tags)
