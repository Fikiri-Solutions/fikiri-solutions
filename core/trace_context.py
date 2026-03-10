#!/usr/bin/env python3
"""
Trace Context Management
Manages trace IDs across request boundaries, background jobs, and async operations.
"""

import uuid
import logging
from typing import Optional
from contextvars import ContextVar
from flask import g, request, has_request_context

logger = logging.getLogger(__name__)

# Context variable for trace ID (works across async boundaries)
_trace_id: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)

def get_trace_id() -> str:
    """
    Get current trace ID, creating one if it doesn't exist.
    
    Priority:
    1. Flask request context (g.trace_id)
    2. Context variable (for async/background jobs)
    3. Generate new UUID
    """
    # Try Flask request context first
    if has_request_context():
        if not hasattr(g, 'trace_id') or not g.trace_id:
            g.trace_id = str(uuid.uuid4())
        return g.trace_id
    
    # Try context variable (for async/background jobs)
    trace_id = _trace_id.get()
    if trace_id:
        return trace_id
    
    # Generate new trace ID
    new_trace_id = str(uuid.uuid4())
    _trace_id.set(new_trace_id)
    return new_trace_id

def set_trace_id(trace_id: Optional[str] = None) -> str:
    """
    Set trace ID for current context.
    
    Args:
        trace_id: Optional trace ID (generates new one if None)
    
    Returns:
        The trace ID that was set
    """
    if trace_id is None:
        trace_id = str(uuid.uuid4())
    
    # Set in Flask request context if available
    if has_request_context():
        g.trace_id = trace_id
    
    # Set in context variable (for async/background jobs)
    _trace_id.set(trace_id)
    
    return trace_id

def clear_trace_id():
    """Clear trace ID from current context"""
    if has_request_context() and hasattr(g, 'trace_id'):
        delattr(g, 'trace_id')
    _trace_id.set(None)

def init_trace_context(app):
    """
    Initialize trace context middleware for Flask app.
    
    This adds before_request and after_request handlers to:
    - Extract trace ID from request headers (X-Trace-ID)
    - Set trace ID in Flask g context
    - Add trace ID to response headers
    """
    @app.before_request
    def before_request():
        """Extract or generate trace ID for request"""
        # Check for trace ID in request headers (only X-Trace-ID, not X-Request-ID)
        trace_id = request.headers.get('X-Trace-ID')
        if not trace_id:
            trace_id = str(uuid.uuid4())
        
        # Set in Flask g context
        g.trace_id = trace_id
        
        # Also set in context variable for async operations
        _trace_id.set(trace_id)
    
    @app.after_request
    def after_request(response):
        """Add trace ID to response headers"""
        if hasattr(g, 'trace_id'):
            response.headers['X-Trace-ID'] = g.trace_id
        return response
