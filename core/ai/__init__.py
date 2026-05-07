"""
Fikiri Solutions - AI Pipeline Module
Centralized LLM routing, client management, validation, and canonical schemas.
"""

from core.ai.llm_router import LLMRouter, INTENT_MODEL_CONFIG, KNOWN_INTENTS
from core.ai.model_policy import FALLBACK_LLM_MODEL, PREMIUM_LLM_MODEL
from core.ai.llm_client import LLMClient
from core.ai.validators import SchemaValidator
from core.ai.eval_thresholds import EmailTriageEvalThresholds
from core.ai.embedding_client import get_embedding, is_embedding_available, get_embedding_dimension

# Canonical schemas for LLM and ingestion (see docs/SCHEMA_STRATEGY_LLM_DATA.md)
from core.ai import schemas as ai_schemas

__all__ = [
    'LLMRouter', 'INTENT_MODEL_CONFIG', 'KNOWN_INTENTS',
    'FALLBACK_LLM_MODEL', 'PREMIUM_LLM_MODEL',
    'LLMClient', 'SchemaValidator',
    'EmailTriageEvalThresholds',
    'get_embedding', 'is_embedding_available', 'get_embedding_dimension',
    'ai_schemas',
]

