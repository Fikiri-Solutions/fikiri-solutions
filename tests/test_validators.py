"""
Unit tests for core/ai/validators.py (SchemaValidator).
"""

import os
import sys
import json

os.environ.setdefault("FLASK_ENV", "test")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai.validators import SchemaValidator


class TestSchemaValidator:
    def test_validate_schema_string_json_valid(self):
        v = SchemaValidator()
        schema = {"type": "object", "required": ["a"], "properties": {"a": {"type": "string"}}}
        assert v.validate_schema('{"a": "hello"}', schema) is True

    def test_validate_schema_string_json_missing_required_false(self):
        v = SchemaValidator()
        schema = {"type": "object", "required": ["a", "b"], "properties": {"a": {"type": "string"}, "b": {"type": "integer"}}}
        assert v.validate_schema('{"a": "x"}', schema) is False

    def test_validate_schema_string_simple_type_string(self):
        v = SchemaValidator()
        assert v.validate_schema("plain text", {"type": "string"}) is True

    def test_validate_schema_dict_valid(self):
        v = SchemaValidator()
        schema = {"required": ["name"], "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}}
        assert v.validate_schema({"name": "Alice", "age": 30}, schema) is True

    def test_validate_schema_dict_wrong_type_false(self):
        v = SchemaValidator()
        schema = {"required": ["age"], "properties": {"age": {"type": "integer"}}}
        assert v.validate_schema({"age": "not a number"}, schema) is False

    def test_validate_type_string(self):
        v = SchemaValidator()
        assert v._validate_type("hello", {"type": "string"}) is True
        assert v._validate_type(123, {"type": "string"}) is False

    def test_validate_type_number(self):
        v = SchemaValidator()
        assert v._validate_type(1.5, {"type": "number"}) is True
        assert v._validate_type(1, {"type": "number"}) is True
        assert v._validate_type("1", {"type": "number"}) is False

    def test_validate_type_array(self):
        v = SchemaValidator()
        assert v._validate_type([1, 2], {"type": "array"}) is True
        assert v._validate_type([1, 2], {"type": "array", "items": {"type": "integer"}}) is True
        assert v._validate_type([1, "x"], {"type": "array", "items": {"type": "integer"}}) is False

    def test_create_schema_from_example(self):
        v = SchemaValidator()
        example = {"name": "Alice", "count": 5, "active": True}
        schema = v.create_schema(example)
        assert schema["type"] == "object"
        assert set(schema["required"]) == {"name", "count", "active"}
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["count"]["type"] == "integer"
        # bool is inferred as integer in Python (isinstance(True, int) is True)
        assert schema["properties"]["active"]["type"] in ("boolean", "integer")

    def test_infer_type_nested(self):
        v = SchemaValidator()
        example = {"nested": {"a": 1}}
        schema = v.create_schema(example)
        assert schema["properties"]["nested"]["type"] == "object"
        assert "a" in schema["properties"]["nested"].get("properties", {})
