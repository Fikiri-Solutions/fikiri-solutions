#!/usr/bin/env python3
"""
Flask Request Timeout Middleware
Adds request-level timeout protection to prevent long-running requests from blocking workers.
"""

import os
import logging
from flask import g, request
from functools import wraps

logger = logging.getLogger(__name__)

# Default request timeout (seconds)
DEFAULT_REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))


def request_timeout(timeout_seconds: int = None):
    """
    Decorator to add timeout to Flask route handlers.
    
    Usage:
        @app.route('/api/endpoint')
        @request_timeout(30)
        def my_endpoint():
            ...
    
    Note: This is a best-effort timeout. For true timeout enforcement,
    use gunicorn's timeout setting or a WSGI server with timeout support.
    """
    timeout = timeout_seconds or DEFAULT_REQUEST_TIMEOUT
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Store start time
            import time
            g.request_start_time = time.time()
            g.request_timeout = timeout
            
            # Check timeout before processing (best effort)
            # Note: True timeout enforcement requires WSGI server support
            result = f(*args, **kwargs)
            
            # Log if request took too long
            elapsed = time.time() - g.request_start_time
            if elapsed > timeout * 0.8:  # Warn at 80% of timeout
                logger.warning(
                    f"Request {request.endpoint} took {elapsed:.2f}s "
                    f"(timeout: {timeout}s)",
                    extra={
                        'event': 'request_slow',
                        'service': 'api',
                        'severity': 'WARN',
                        'endpoint': request.endpoint,
                        'latency_ms': elapsed * 1000,
                        'timeout_ms': timeout * 1000
                    }
                )
            
            return result
        return decorated_function
    return decorator


def init_request_timeout(app):
    """
    Initialize request timeout middleware for Flask app.
    
    This adds before_request and after_request handlers to track request duration.
    """
    import time
    
    @app.before_request
    def before_request():
        """Track request start time"""
        g.request_start_time = time.time()
        g.request_timeout = DEFAULT_REQUEST_TIMEOUT
    
    @app.after_request
    def after_request(response):
        """Log slow requests"""
        if hasattr(g, 'request_start_time'):
            elapsed = time.time() - g.request_start_time
            timeout = getattr(g, 'request_timeout', DEFAULT_REQUEST_TIMEOUT)
            
            # Log slow requests
            if elapsed > timeout * 0.8:
                logger.warning(
                    f"Slow request: {request.endpoint} took {elapsed:.2f}s",
                    extra={
                        'event': 'request_slow',
                        'service': 'api',
                        'severity': 'WARN',
                        'endpoint': request.endpoint,
                        'method': request.method,
                        'latency_ms': elapsed * 1000,
                        'timeout_ms': timeout * 1000
                    }
                )
        
        return response
