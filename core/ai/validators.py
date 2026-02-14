#!/usr/bin/env python3
"""
Fikiri Solutions - Schema Validators
Validates LLM outputs against expected schemas to ensure structured responses.
"""

import logging
import json
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger(__name__)

class SchemaValidator:
    """
    Validates LLM outputs against expected schemas.
    Ensures all AI responses are structured and validated before use.
    """
    
    def __init__(self):
        """Initialize schema validator."""
        self._initialized = True
    
    def validate_schema(self, output: Union[str, Dict[str, Any]], schema: Dict[str, Any]) -> bool:
        """
        Validate output against a schema definition.
        
        Args:
            output: LLM output (string or dict)
            schema: Schema definition with expected structure
        
        Returns:
            True if valid, False otherwise
        """
        try:
            # If output is string, try to parse as JSON
            if isinstance(output, str):
                try:
                    output = json.loads(output)
                except json.JSONDecodeError:
                    # If not JSON, check if it's a simple string schema
                    if schema.get('type') == 'string':
                        return True
                    return False
            
            # Validate against schema
            return self._validate_dict(output, schema)
            
        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            return False
    
    def _validate_dict(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate dictionary against schema."""
        # Check required fields
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Check field types
        properties = schema.get('properties', {})
        for field, value in data.items():
            if field in properties:
                field_schema = properties[field]
                if not self._validate_type(value, field_schema):
                    logger.warning(f"Field {field} does not match schema type")
                    return False
        
        return True
    
    def _validate_type(self, value: Any, field_schema: Dict[str, Any]) -> bool:
        """Validate a single value against field schema."""
        expected_type = field_schema.get('type')
        
        if expected_type == 'string':
            return isinstance(value, str)
        elif expected_type == 'integer':
            return isinstance(value, int)
        elif expected_type == 'number':
            return isinstance(value, (int, float))
        elif expected_type == 'boolean':
            return isinstance(value, bool)
        elif expected_type == 'array':
            if not isinstance(value, list):
                return False
            items_schema = field_schema.get('items', {})
            if items_schema:
                return all(self._validate_type(item, items_schema) for item in value)
            return True
        elif expected_type == 'object':
            if not isinstance(value, dict):
                return False
            properties = field_schema.get('properties', {})
            if properties:
                return self._validate_dict(value, field_schema)
            return True
        
        return True  # Unknown type, allow it
    
    def create_schema(self, example: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a schema from an example dictionary.
        Useful for generating schemas from sample outputs.
        
        Args:
            example: Example dictionary
        
        Returns:
            Schema definition
        """
        schema = {
            'type': 'object',
            'properties': {},
            'required': list(example.keys())
        }
        
        for key, value in example.items():
            schema['properties'][key] = self._infer_type(value)
        
        return schema
    
    def _infer_type(self, value: Any) -> Dict[str, Any]:
        """Infer schema type from value."""
        if isinstance(value, str):
            return {'type': 'string'}
        elif isinstance(value, int):
            return {'type': 'integer'}
        elif isinstance(value, float):
            return {'type': 'number'}
        elif isinstance(value, bool):
            return {'type': 'boolean'}
        elif isinstance(value, list):
            if value:
                return {'type': 'array', 'items': self._infer_type(value[0])}
            return {'type': 'array'}
        elif isinstance(value, dict):
            return {
                'type': 'object',
                'properties': {k: self._infer_type(v) for k, v in value.items()}
            }
        else:
            return {'type': 'string'}  # Default to string
