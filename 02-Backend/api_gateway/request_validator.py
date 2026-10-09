import re
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class ValidationError(Exception):
    pass


class ValidationMode(Enum):
    STRICT = "strict"
    LAX = "lax"


@dataclass
class FieldRule:
    field_name: str
    required: bool = True
    field_type: str = "string"
    min_length: int = 0
    max_length: int = 4096
    pattern: str = ""
    allowed_values: Optional[List[Any]] = None
    custom_validator: Optional[Callable[[Any], bool]] = None


@dataclass
class ValidationResult:
    is_valid: bool
    errors: Dict[str, str]
    data: Dict[str, Any]


class RequestValidator:
    def __init__(self, mode: ValidationMode = ValidationMode.STRICT):
        self._mode = mode
        self._schemas: Dict[str, List[FieldRule]] = {}

    def register_schema(self, name: str, rules: List[FieldRule]):
        self._schemas[name] = rules

    def validate(self, schema_name: str, data: Dict[str, Any]) -> ValidationResult:
        rules = self._schemas.get(schema_name, [])
        if not rules:
            return ValidationResult(is_valid=True, errors={}, data=data)
        errors: Dict[str, str] = {}
        validated_data: Dict[str, Any] = {}
        for rule in rules:
            value = data.get(rule.field_name)
            if rule.required and (value is None or (isinstance(value, str) and value == "")):
                errors[rule.field_name] = "required"
                continue
            if value is None:
                continue
            if rule.pattern and isinstance(value, str):
                if not re.match(rule.pattern, value):
                    errors[rule.field_name] = "pattern_mismatch"
                    continue
            if rule.allowed_values is not None:
                if value not in rule.allowed_values:
                    errors[rule.field_name] = "not_allowed"
                    continue
            if rule.custom_validator is not None:
                try:
                    ok = rule.custom_validator(value)
                except Exception:
                    errors[rule.field_name] = "validator_error"
                    continue
                if not ok:
                    errors[rule.field_name] = "custom_failed"
                    continue
            validated_data[rule.field_name] = value
        is_valid = not errors
        return ValidationResult(is_valid=is_valid, errors=errors, data=validated_data)

    def validate_headers(self, headers: Dict[str, str], required: Set[str]) -> ValidationResult:
        errors: Dict[str, str] = {}
        for hdr in required:
            if hdr not in headers:
                errors[hdr] = "missing_header"
        return ValidationResult(is_valid=not errors, errors=errors, data=dict(headers))
