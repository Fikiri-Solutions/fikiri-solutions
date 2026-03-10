#!/usr/bin/env python3
"""
Fikiri Solutions - LLM Client
Handles actual LLM API calls with retry logic, error handling, and cost tracking.
"""

import os
import time
import logging
import uuid
import random
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Import circuit breaker
try:
    from core.circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError
    CIRCUIT_BREAKER_AVAILABLE = True
except ImportError:
    CIRCUIT_BREAKER_AVAILABLE = False
    logger.warning("Circuit breaker not available")

# Default timeout for OpenAI API calls (seconds)
DEFAULT_OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "30"))

class LLMClient:
    """
    Centralized LLM client with exponential backoff, cost tracking, and error handling.
    All LLM API calls must go through this client.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize LLM client with OpenAI API key."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        test_mode = os.getenv("FIKIRI_TEST_MODE") == "1"
        self.enabled = bool(self.api_key) and not test_mode
        
        if self.enabled:
            try:
                import openai
                
                # OpenAI version compatibility
                if hasattr(openai, 'OpenAI'):
                    self.client = openai.OpenAI(api_key=self.api_key)
                    logger.info("✅ LLM client initialized (OpenAI v1.0+)")
                else:
                    # Legacy OpenAI < 1.0.0
                    openai.api_key = self.api_key
                    self.client = openai
                    logger.info("✅ LLM client initialized (OpenAI legacy)")
            except ImportError:
                logger.warning("⚠️ OpenAI not installed. Run: pip install openai")
                self.enabled = False
            except Exception as e:
                logger.error(f"⚠️ LLM client initialization failed: {e}")
                self.enabled = False
        else:
            if not test_mode:
                logger.warning("⚠️ No OpenAI API key found. Set OPENAI_API_KEY environment variable")
    
    def is_enabled(self) -> bool:
        """Check if LLM client is enabled."""
        return self.enabled and self.client is not None
    
    def call_llm(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Call LLM with exponential backoff, error handling, and cost tracking.
        
        Args:
            model: Model name (e.g., "gpt-3.5-turbo", "gpt-4")
            prompt: User prompt
            max_tokens: Maximum tokens to generate (bounded, required)
            temperature: Temperature (0.0-2.0, default 0.7)
            system_message: Optional system message
            messages: Optional pre-formatted messages list
            trace_id: Optional trace ID for logging
        
        Returns:
            Dict with:
                - success: bool
                - content: str (response text)
                - tokens_used: int
                - cost_usd: float
                - latency_ms: float
                - model: str
                - trace_id: str
                - error: Optional[str]
        """
        trace_id = trace_id or str(uuid.uuid4())
        start_time = time.time()
        
        # Validate inputs
        if not self.is_enabled():
            return {
                'success': False,
                'content': '',
                'tokens_used': 0,
                'cost_usd': 0.0,
                'latency_ms': 0.0,
                'model': model,
                'trace_id': trace_id,
                'error': 'LLM client not enabled'
            }
        
        # Bound temperature and max_tokens
        temperature = max(0.0, min(2.0, temperature))
        max_tokens = max(1, min(4000, max_tokens))  # Reasonable bounds
        
        # Prepare messages
        if messages is None:
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})
        
        # Get circuit breaker for OpenAI
        breaker = None
        if CIRCUIT_BREAKER_AVAILABLE:
            breaker = get_circuit_breaker(
                "openai",
                failure_threshold=5,
                success_threshold=2,
                timeout_seconds=60,
                fail_open=True  # Fail open: allow requests but return error
            )
        
        # Retry with exponential backoff
        max_retries = 3
        base_delay = 1.0
        
        def _call_openai():
            """Inner function to call OpenAI API with timeout"""
            # Call OpenAI API with timeout
            if hasattr(self.client, 'chat'):
                # OpenAI >= 1.0.0 - use timeout parameter
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=DEFAULT_OPENAI_TIMEOUT
                )
                content = response.choices[0].message.content.strip()
                tokens_used = response.usage.total_tokens if response.usage else 0
            else:
                # Legacy OpenAI < 1.0.0 - wrap in timeout manually
                import signal
                def timeout_handler(signum, frame):
                    raise TimeoutError(f"OpenAI API call timed out after {DEFAULT_OPENAI_TIMEOUT}s")
                
                # Set timeout signal (Unix only)
                if hasattr(signal, 'SIGALRM'):
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(DEFAULT_OPENAI_TIMEOUT)
                
                try:
                    response = self.client.ChatCompletion.create(
                        model=model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    content = response.choices[0].message.content.strip()
                    tokens_used = response.usage.total_tokens if response.usage else 0
                finally:
                    if hasattr(signal, 'SIGALRM'):
                        signal.alarm(0)  # Cancel alarm
            
            return content, tokens_used
        
        for attempt in range(max_retries):
            try:
                # Use circuit breaker if available
                if breaker:
                    content, tokens_used = breaker.call(_call_openai)
                else:
                    content, tokens_used = _call_openai()
                
                # Calculate cost and latency
                latency_ms = (time.time() - start_time) * 1000
                cost_usd = self._calculate_cost(model, tokens_used)
                
                # Log success
                logger.info(
                    f"✅ LLM call successful",
                    extra={
                        'event': 'llm_call_success',
                        'service': 'ai',
                        'severity': 'INFO',
                        'trace_id': trace_id,
                        'model': model,
                        'tokens_used': tokens_used,
                        'cost_usd': cost_usd,
                        'latency_ms': latency_ms,
                        'metadata': {'max_tokens': max_tokens, 'temperature': temperature}
                    }
                )
                
                return {
                    'success': True,
                    'content': content,
                    'tokens_used': tokens_used,
                    'cost_usd': cost_usd,
                    'latency_ms': latency_ms,
                    'model': model,
                    'trace_id': trace_id,
                    'error': None
                }
                
            except TimeoutError as e:
                # Timeout error
                latency_ms = (time.time() - start_time) * 1000
                error_msg = str(e)
                logger.warning(f"LLM call timed out after {DEFAULT_OPENAI_TIMEOUT}s")
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                    time.sleep(delay)
                    continue
                else:
                    return {
                        'success': False,
                        'content': '',
                        'tokens_used': 0,
                        'cost_usd': 0.0,
                        'latency_ms': latency_ms,
                        'model': model,
                        'trace_id': trace_id,
                        'error': error_msg,
                        'error_type': 'timeout'
                    }
            except CircuitBreakerOpenError as e:
                # Circuit breaker is open
                latency_ms = (time.time() - start_time) * 1000
                error_msg = str(e)
                logger.warning(f"Circuit breaker OPEN for OpenAI: {error_msg}")
                
                return {
                    'success': False,
                    'content': '',
                    'tokens_used': 0,
                    'cost_usd': 0.0,
                    'latency_ms': latency_ms,
                    'model': model,
                    'trace_id': trace_id,
                    'error': 'Service temporarily unavailable (circuit breaker open)',
                    'error_type': 'circuit_breaker_open'
                }
            except Exception as e:
                error_msg = str(e)
                error_lower = error_msg.lower()
                latency_ms = (time.time() - start_time) * 1000
                
                # Detect error type
                if 'quota' in error_lower or 'billing' in error_lower:
                    error_type = 'insufficient_quota'
                    user_msg = 'OpenAI API quota exceeded. Check your account balance.'
                elif '401' in error_msg or ('unauthorized' in error_lower and 'api' in error_lower):
                    error_type = 'authentication_error'
                    user_msg = 'OpenAI API key is invalid. Check OPENAI_API_KEY.'
                elif '429' in error_msg or 'rate limit' in error_lower:
                    error_type = 'rate_limit'
                    user_msg = 'Rate limit exceeded. Wait and retry.'
                elif 'model' in error_lower and ('not found' in error_lower or 'invalid' in error_lower):
                    error_type = 'model_error'
                    user_msg = f'Model {model} unavailable. Falling back to gpt-3.5-turbo.'
                    if model != 'gpt-3.5-turbo' and attempt == 0:
                        model = 'gpt-3.5-turbo'
                        continue
                else:
                    error_type = 'unknown'
                    user_msg = error_msg
                
                logger.error(f"LLM call failed (attempt {attempt + 1}/{max_retries}): {user_msg}")
                
                # Don't retry on quota/auth errors
                if error_type in ('insufficient_quota', 'authentication_error'):
                    return {
                        'success': False,
                        'content': '',
                        'tokens_used': 0,
                        'cost_usd': 0.0,
                        'latency_ms': latency_ms,
                        'model': model,
                        'trace_id': trace_id,
                        'error': error_msg,
                        'error_type': error_type
                    }
                
                # Retry with exponential backoff + jitter for other errors
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)  # Jitter
                    time.sleep(delay)
                    continue
                else:
                    # Final attempt failed
                    return {
                        'success': False,
                        'content': '',
                        'tokens_used': 0,
                        'cost_usd': 0.0,
                        'latency_ms': latency_ms,
                        'model': model,
                        'trace_id': trace_id,
                        'error': error_msg,
                        'error_type': error_type
                    }
        
        # Should not reach here, but return error if we do
        return {
            'success': False,
            'content': '',
            'tokens_used': 0,
            'cost_usd': 0.0,
            'latency_ms': (time.time() - start_time) * 1000,
            'model': model,
            'trace_id': trace_id,
            'error': 'Max retries exceeded'
        }
    
    def _calculate_cost(self, model: str, tokens: int) -> float:
        """
        Calculate cost in USD based on model and token usage.
        Uses approximate pricing as of 2024.
        """
        # Pricing per 1K tokens (approximate)
        pricing = {
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
            'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002},
            'gpt-3.5-turbo-16k': {'input': 0.003, 'output': 0.004},
        }
        
        # Default to gpt-3.5-turbo pricing if model not found
        model_pricing = pricing.get(model, pricing['gpt-3.5-turbo'])
        
        # Rough estimate: assume 70% input, 30% output tokens
        input_tokens = int(tokens * 0.7)
        output_tokens = int(tokens * 0.3)
        
        cost = (input_tokens / 1000 * model_pricing['input']) + \
               (output_tokens / 1000 * model_pricing['output'])
        
        return round(cost, 6)
