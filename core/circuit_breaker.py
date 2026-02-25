#!/usr/bin/env python3
"""
Circuit Breaker Pattern Implementation
Protects against cascading failures from external API dependencies.

Circuit states:
- CLOSED: Normal operation, requests pass through
- OPEN: Service is failing, requests fail fast
- HALF_OPEN: Testing if service recovered, allows limited requests
"""

import time
import logging
from enum import Enum
from typing import Dict, Any, Optional, Callable
from threading import Lock
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, fail fast
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker for external API calls.
    
    Fails open (allows requests but returns error) or fails closed (blocks requests)
    based on failure threshold and time window.
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: int = 60,
        fail_open: bool = True,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Service name (e.g., "openai", "gmail", "stripe")
            failure_threshold: Number of failures to open circuit
            success_threshold: Number of successes in half-open to close circuit
            timeout_seconds: Time window for failure counting
            fail_open: If True, allow requests but return error; if False, block requests
            expected_exception: Exception type that counts as failure
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self.fail_open = fail_open
        self.expected_exception = expected_exception
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change: datetime = datetime.now()
        self.lock = Lock()
        
        logger.info(f"Circuit breaker '{name}' initialized (fail_open={fail_open})")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to call
            *args, **kwargs: Arguments to pass to function
        
        Returns:
            Function result
        
        Raises:
            CircuitBreakerOpenError: If circuit is open and fail_open=False
            Exception: Original exception if circuit is open and fail_open=True
        """
        with self.lock:
            # Check if circuit should transition from OPEN to HALF_OPEN
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    self.last_state_change = datetime.now()
                elif not self.fail_open:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is OPEN. Service unavailable."
                    )
            
            # If OPEN and fail_open=True, allow request but it will likely fail
            if self.state == CircuitState.OPEN and self.fail_open:
                logger.warning(f"Circuit breaker '{self.name}' is OPEN (fail_open=True), allowing request")
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
        except Exception as e:
            # Unexpected exception - log but don't count as circuit breaker failure
            logger.warning(f"Circuit breaker '{self.name}' caught unexpected exception: {e}")
            raise
    
    def _on_success(self):
        """Handle successful call"""
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    logger.info(f"Circuit breaker '{self.name}' transitioning to CLOSED")
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    self.last_state_change = datetime.now()
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.state == CircuitState.HALF_OPEN:
                # Failure in half-open state -> back to open
                logger.warning(f"Circuit breaker '{self.name}' transitioning back to OPEN")
                self.state = CircuitState.OPEN
                self.success_count = 0
                self.last_state_change = datetime.now()
            elif self.state == CircuitState.CLOSED:
                # Check if threshold exceeded
                if self.failure_count >= self.failure_threshold:
                    logger.error(
                        f"Circuit breaker '{self.name}' opening after {self.failure_count} failures "
                        f"(threshold: {self.failure_threshold})"
                    )
                    self.state = CircuitState.OPEN
                    self.last_state_change = datetime.now()
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_state_change is None:
            return True
        
        elapsed = (datetime.now() - self.last_state_change).total_seconds()
        return elapsed >= self.timeout_seconds
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        with self.lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
                "last_state_change": self.last_state_change.isoformat(),
                "fail_open": self.fail_open,
                "failure_threshold": self.failure_threshold,
                "timeout_seconds": self.timeout_seconds
            }
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state"""
        with self.lock:
            logger.info(f"Circuit breaker '{self.name}' manually reset")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            self.last_state_change = datetime.now()


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and fail_open=False"""
    pass


class CircuitBreakerManager:
    """Manages multiple circuit breakers"""
    
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
        self.lock = Lock()
    
    def get_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: int = 60,
        fail_open: bool = True
    ) -> CircuitBreaker:
        """Get or create circuit breaker"""
        with self.lock:
            if name not in self.breakers:
                self.breakers[name] = CircuitBreaker(
                    name=name,
                    failure_threshold=failure_threshold,
                    success_threshold=success_threshold,
                    timeout_seconds=timeout_seconds,
                    fail_open=fail_open
                )
            return self.breakers[name]
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        with self.lock:
            return {name: breaker.get_status() for name, breaker in self.breakers.items()}
    
    def reset_breaker(self, name: str):
        """Reset a specific circuit breaker"""
        with self.lock:
            if name in self.breakers:
                self.breakers[name].reset()


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Get circuit breaker instance"""
    return circuit_breaker_manager.get_breaker(name, **kwargs)
