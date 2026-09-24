"""Configuration validation against a schema."""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    pass


class ConfigValidator:
    def __init__(self) -> None:
        self._schema: Dict[str, Any] = {}
        self._errors: List[str] = []

    def schema(self, schema: Dict[str, Any]) -> None:
        self._schema = schema

    def _validate_type(self, value: Any, expected_type: Any) -> bool:
        return isinstance(value, expected_type)

    def _validate_required(self, config: Dict[str, Any], schema: Dict[str, Any]) -> None:
        for key, value in schema.items():
            if isinstance(value, dict) and value.get("required", False):
                if key not in config:
                    self._errors.append(f"missing required config: {key}")

    def _validate_range(self, value: Any, schema: Dict[str, Any]) -> None:
        if not isinstance(value, (int, float)):
            return
        if "min" in schema and value < schema["min"]:
            self._errors.append(f"{schema.get('name', 'value')} below min")
        if "max" in schema and value > schema["max"]:
            self._errors.append(f"{schema.get('name', 'value')} above max")

    def _validate_items(self, config: Dict[str, Any], schema: Dict[str, Any]) -> None:
        for key, value in schema.items():
            if key not in config:
                continue
            cfg_value = config[key]
            self._validate_range(cfg_value, value)

    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        self._errors = []
        self._validate_required(config, self._schema)
        self._validate_items(config, self._schema)
        for key, value in config.items():
            if key in self._schema:
                self._validate_range(value, self._schema[key])
        return len(self._errors) == 0, list(self._errors)
