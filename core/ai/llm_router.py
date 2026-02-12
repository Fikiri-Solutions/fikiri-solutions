#!/usr/bin/env python3
"""
Fikiri Solutions - LLM Router
Routes LLM requests through the proper pipeline: preprocess → detect_intent → choose_model → call_llm → postprocess → validate → log → return
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.ai.llm_client import LLMClient
from core.ai.validators import SchemaValidator

logger = logging.getLogger(__name__)

class LLMRouter:
    """
    Central router for all LLM operations.
    Implements the required pipeline: preprocess → detect_intent → choose_model → call_llm → postprocess → validate → log → return
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize LLM router with client and validator."""
        self.client = LLMClient(api_key)
        self.validator = SchemaValidator()
        self.trace_id = None
    
    def process(
        self,
        input_data: str,
        intent: Optional[str] = None,
        cost_budget: Optional[float] = None,
        latency_requirement: Optional[str] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process input through the complete AI pipeline.
        
        Pipeline:
        1. preprocess(input)
        2. detect_intent(input) [if not provided]
        3. choose_model(intent, cost_budget, latency_requirement)
        4. call_llm(model, prompt, params)
        5. postprocess(output)
        6. validate_schema(output)
        7. log cost + latency
        8. return structured result
        
        Args:
            input_data: Input text/prompt
            intent: Optional pre-detected intent (skips detection step)
            cost_budget: Optional cost budget in USD
            latency_requirement: Optional latency requirement ('low', 'medium', 'high')
            output_schema: Optional schema for validation
            context: Optional context dictionary
        
        Returns:
            Dict with:
                - success: bool
                - content: str
                - intent: str
                - model: str
                - tokens_used: int
                - cost_usd: float
                - latency_ms: float
                - trace_id: str
                - validated: bool
                - error: Optional[str]
        """
        self.trace_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            # Step 1: Preprocess
            preprocessed = self.preprocess(input_data, context)
            
            # Step 2: Detect intent (if not provided)
            if not intent:
                intent = self.detect_intent(preprocessed)
            
            # Step 3: Choose model
            model_config = self.choose_model(intent, cost_budget, latency_requirement)
            model = model_config['model']
            max_tokens = model_config['max_tokens']
            temperature = model_config['temperature']
            
            # Step 4: Call LLM
            llm_result = self.client.call_llm(
                model=model,
                prompt=preprocessed,
                max_tokens=max_tokens,
                temperature=temperature,
                trace_id=self.trace_id
            )
            
            if not llm_result['success']:
                return {
                    'success': False,
                    'content': '',
                    'intent': intent,
                    'model': model,
                    'tokens_used': 0,
                    'cost_usd': 0.0,
                    'latency_ms': llm_result['latency_ms'],
                    'trace_id': self.trace_id,
                    'validated': False,
                    'error': llm_result.get('error', 'LLM call failed')
                }
            
            # Step 5: Postprocess
            postprocessed = self.postprocess(llm_result['content'], intent, context)
            
            # Step 6: Validate schema (if provided)
            validated = False
            if output_schema:
                validated = self.validator.validate_schema(postprocessed, output_schema)
                if not validated:
                    logger.warning(
                        f"Schema validation failed for trace_id {self.trace_id}",
                        extra={
                            'event': 'schema_validation_failed',
                            'service': 'ai',
                            'severity': 'WARN',
                            'trace_id': self.trace_id
                        }
                    )
            else:
                validated = True  # No schema to validate against
            
            # Step 7: Log cost + latency (already logged in client, but log summary)
            total_latency = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(
                f"✅ AI pipeline completed",
                extra={
                    'event': 'ai_pipeline_complete',
                    'service': 'ai',
                    'severity': 'INFO',
                    'trace_id': self.trace_id,
                    'intent': intent,
                    'model': model,
                    'tokens_used': llm_result['tokens_used'],
                    'cost_usd': llm_result['cost_usd'],
                    'latency_ms': total_latency,
                    'validated': validated,
                    'metadata': {'cost_budget': cost_budget, 'latency_requirement': latency_requirement}
                }
            )
            
            # Step 8: Return structured result
            return {
                'success': True,
                'content': postprocessed,
                'intent': intent,
                'model': model,
                'tokens_used': llm_result['tokens_used'],
                'cost_usd': llm_result['cost_usd'],
                'latency_ms': total_latency,
                'trace_id': self.trace_id,
                'validated': validated,
                'error': None
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"❌ AI pipeline failed: {error_msg}",
                extra={
                    'event': 'ai_pipeline_error',
                    'service': 'ai',
                    'severity': 'ERROR',
                    'trace_id': self.trace_id,
                    'error': error_msg
                }
            )
            return {
                'success': False,
                'content': '',
                'intent': intent or 'unknown',
                'model': 'unknown',
                'tokens_used': 0,
                'cost_usd': 0.0,
                'latency_ms': 0.0,
                'trace_id': self.trace_id,
                'validated': False,
                'error': error_msg
            }
    
    def preprocess(self, input_data: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Preprocess input: sanitize, truncate if needed, add context.
        
        Args:
            input_data: Raw input text
            context: Optional context dictionary
        
        Returns:
            Preprocessed prompt string
        """
        # Sanitize: remove excessive whitespace, basic cleanup
        preprocessed = ' '.join(input_data.split())
        
        # Add context if provided
        if context:
            context_str = f"\n\nContext: {context.get('context', '')}"
            preprocessed = preprocessed + context_str
        
        # Truncate if too long (prevent token overflow)
        max_length = 8000  # Reasonable limit for most models
        if len(preprocessed) > max_length:
            preprocessed = preprocessed[:max_length] + "... [truncated]"
            logger.warning(f"Input truncated to {max_length} characters")
        
        return preprocessed
    
    def detect_intent(self, input_data: str) -> str:
        """
        Detect intent from input using simple keyword matching.
        Can be enhanced with ML model later.
        
        Args:
            input_data: Preprocessed input
        
        Returns:
            Intent string (e.g., 'email_reply', 'classification', 'extraction', 'general')
        """
        input_lower = input_data.lower()
        
        # Simple keyword-based intent detection
        if any(word in input_lower for word in ['reply', 'respond', 'answer', 'email']):
            return 'email_reply'
        elif any(word in input_lower for word in ['classify', 'categorize', 'type', 'category']):
            return 'classification'
        elif any(word in input_lower for word in ['extract', 'parse', 'find', 'get']):
            return 'extraction'
        elif any(word in input_lower for word in ['summarize', 'summary', 'summarise']):
            return 'summarization'
        else:
            return 'general'
    
    def choose_model(
        self,
        intent: str,
        cost_budget: Optional[float] = None,
        latency_requirement: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Choose appropriate model based on intent, cost budget, and latency requirements.
        
        Args:
            intent: Detected intent
            cost_budget: Optional cost budget in USD
            latency_requirement: Optional latency requirement ('low', 'medium', 'high')
        
        Returns:
            Dict with model, max_tokens, temperature
        """
        # Default model selection based on intent
        model_selection = {
            'email_reply': {'model': 'gpt-3.5-turbo', 'max_tokens': 300, 'temperature': 0.7},
            'classification': {'model': 'gpt-3.5-turbo', 'max_tokens': 100, 'temperature': 0.3},
            'extraction': {'model': 'gpt-3.5-turbo', 'max_tokens': 200, 'temperature': 0.1},
            'summarization': {'model': 'gpt-3.5-turbo', 'max_tokens': 500, 'temperature': 0.5},
            'general': {'model': 'gpt-3.5-turbo', 'max_tokens': 500, 'temperature': 0.7}
        }
        
        config = model_selection.get(intent, model_selection['general']).copy()
        
        # Adjust based on cost budget
        if cost_budget is not None:
            if cost_budget < 0.01:  # Very low budget
                config['model'] = 'gpt-3.5-turbo'
                config['max_tokens'] = min(config['max_tokens'], 200)
            elif cost_budget > 0.10:  # High budget
                config['model'] = 'gpt-4-turbo'
                config['max_tokens'] = min(config['max_tokens'] * 2, 2000)
        
        # Adjust based on latency requirement
        if latency_requirement == 'low':
            config['model'] = 'gpt-3.5-turbo'  # Faster model
        elif latency_requirement == 'high':
            config['model'] = 'gpt-4-turbo'  # Better quality, slower
        
        return config
    
    def postprocess(
        self,
        output: str,
        intent: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Postprocess LLM output: clean, format, validate basic structure.
        
        Args:
            output: Raw LLM output
            intent: Intent used for generation
            context: Optional context
        
        Returns:
            Postprocessed output string
        """
        # Basic cleanup
        postprocessed = output.strip()
        
        # Remove common LLM artifacts
        if postprocessed.startswith('"') and postprocessed.endswith('"'):
            postprocessed = postprocessed[1:-1]
        
        # Intent-specific postprocessing
        if intent == 'email_reply':
            # Ensure it doesn't start with "Subject:" or similar
            if postprocessed.lower().startswith('subject:'):
                lines = postprocessed.split('\n', 1)
                if len(lines) > 1:
                    postprocessed = lines[1].strip()
        
        return postprocessed

