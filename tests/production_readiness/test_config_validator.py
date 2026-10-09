"""Tests for production_readiness config_validator."""
from __future__ import annotations

from production_readiness.config_validator import ConfigValidator, ConfigValidationError


def test_valid_config() -> None:
    validator = ConfigValidator()
    validator.schema({
        "host": {"required": True, "min": 0},
        "port": {"min": 1, "max": 65535},
    })
    valid, errors = validator.validate({"host": "localhost", "port": 8080})
    assert valid is True
    assert errors == []


def test_missing_required() -> None:
    validator = ConfigValidator()
    validator.schema({"host": {"required": True}})
    valid, errors = validator.validate({})
    assert valid is False
    assert any("host" in str(e) for e in errors)


def test_range_violation() -> None:
    validator = ConfigValidator()
    validator.schema({"port": {"min": 1, "max": 65535}})
    valid, errors = validator.validate({"port": 0})
    assert valid is False
    assert any("below min" in str(e) for e in errors)
