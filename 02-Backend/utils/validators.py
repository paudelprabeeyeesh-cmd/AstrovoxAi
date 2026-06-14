"""
Request Validation Utilities
Provides decorators and helpers for input validation and sanitization.
"""

import re
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
from flask import request, jsonify


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_username(username: str) -> bool:
    """Validate username (alphanumeric + underscore, 3-20 chars)."""
    pattern = r'^[a-zA-Z0-9_]{3,20}$'
    return re.match(pattern, username) is not None


def validate_password(password: str, min_length: int = 6) -> bool:
    """Validate password (minimum length)."""
    return len(password) >= min_length


def sanitize_string(value: Any, max_length: int = 1000) -> str:
    """Sanitize string input."""
    if value is None:
        return ""
    
    s = str(value).strip()
    
    # Remove control characters
    s = ''.join(c for c in s if ord(c) >= 32 or c in '\n\r\t')
    
    # Truncate if too long
    if len(s) > max_length:
        s = s[:max_length]
    
    return s


def sanitize_integer(value: Any, min_val: int = None, max_val: int = None) -> int:
    """Sanitize integer input."""
    try:
        i = int(value)
        if min_val is not None and i < min_val:
            raise ValidationError(f"Value must be >= {min_val}")
        if max_val is not None and i > max_val:
            raise ValidationError(f"Value must be <= {max_val}")
        return i
    except (ValueError, TypeError):
        raise ValidationError("Invalid integer value")


def require_json(func: Callable) -> Callable:
    """Decorator: Require request to have JSON content."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not request.is_json:
            return jsonify({
                "status": "ERROR",
                "error": "Request must be JSON",
                "code": "INVALID_CONTENT_TYPE"
            }), 400
        return func(*args, **kwargs)
    return wrapper


def require_fields(*fields: str) -> Callable:
    """Decorator: Require specific fields in JSON payload."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            data = request.get_json() or {}
            missing = [f for f in fields if f not in data or not data[f]]
            if missing:
                return jsonify({
                    "status": "ERROR",
                    "error": f"Missing required fields: {', '.join(missing)}",
                    "code": "MISSING_FIELDS",
                    "missing": missing
                }), 400
            return func(*args, **kwargs)
        return wrapper
    return decorator


def sanitize_payload(func: Callable) -> Callable:
    """Decorator: Sanitize all string fields in JSON payload."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        data = request.get_json() or {}
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = sanitize_string(value)
            else:
                sanitized[key] = value
        # Inject sanitized data
        request.sanitized_data = sanitized
        return func(*args, **kwargs)
    return wrapper
