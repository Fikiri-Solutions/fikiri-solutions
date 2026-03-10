#!/usr/bin/env python3
"""
API Timeout Utilities
Helper functions to add timeouts to external API calls.
"""

import os
import logging
from typing import Any, Callable
from functools import wraps
import signal
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Default timeouts (seconds)
DEFAULT_OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "30"))
DEFAULT_GMAIL_TIMEOUT = int(os.getenv("GMAIL_TIMEOUT", "30"))
DEFAULT_STRIPE_TIMEOUT = int(os.getenv("STRIPE_TIMEOUT", "10"))
DEFAULT_REDIS_TIMEOUT = int(os.getenv("REDIS_TIMEOUT", "5"))


class TimeoutError(Exception):
    """Raised when an operation times out"""
    pass


@contextmanager
def timeout_context(seconds: int):
    """
    Context manager for timeouts (Unix only - uses SIGALRM).
    
    Usage:
        with timeout_context(30):
            result = slow_operation()
    """
    if not hasattr(signal, 'SIGALRM'):
        # Windows/other platforms - timeout not supported via signal
        logger.warning("Timeout context not supported on this platform (requires SIGALRM)")
        yield
        return
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds}s")
    
    # Set up signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def with_timeout(timeout_seconds: int):
    """
    Decorator to add timeout to a function.
    
    Usage:
        @with_timeout(30)
        def my_api_call():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if hasattr(signal, 'SIGALRM'):
                with timeout_context(timeout_seconds):
                    return func(*args, **kwargs)
            else:
                # Fallback: just call function (timeout not supported)
                logger.warning(f"Timeout not supported on this platform for {func.__name__}")
                return func(*args, **kwargs)
        return wrapper
    return decorator


def gmail_execute_with_timeout(execute_func, timeout: int = DEFAULT_GMAIL_TIMEOUT):
    """
    Execute Gmail API call with timeout.
    
    Args:
        execute_func: Gmail API execute() call (callable)
        timeout: Timeout in seconds
    
    Returns:
        API response
    
    Raises:
        TimeoutError: If operation exceeds timeout
    """
    if hasattr(signal, 'SIGALRM'):
        with timeout_context(timeout):
            return execute_func()
    else:
        # Fallback: execute without timeout (not ideal but works)
        logger.warning("Gmail timeout not supported on this platform")
        return execute_func()


def stripe_call_with_timeout(func: Callable, *args, timeout: int = DEFAULT_STRIPE_TIMEOUT, **kwargs):
    """
    Execute Stripe API call with timeout.
    
    Note: Stripe Python SDK doesn't accept timeout parameter directly.
    We wrap it in a timeout context.
    
    Args:
        func: Stripe API function to call
        *args, **kwargs: Arguments to pass to function
        timeout: Timeout in seconds
    
    Returns:
        Stripe API response
    
    Raises:
        TimeoutError: If operation exceeds timeout
    """
    if hasattr(signal, 'SIGALRM'):
        with timeout_context(timeout):
            return func(*args, **kwargs)
    else:
        # Fallback: execute without timeout
        logger.warning("Stripe timeout not supported on this platform")
        return func(*args, **kwargs)
