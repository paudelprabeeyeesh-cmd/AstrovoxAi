"""
Utility package for Astravox backend.
Includes logging, middleware, and validation helpers.
"""

from .logger import (
    setup_logger,
    app_logger,
    db_logger,
    ai_logger,
    auth_logger,
    chat_logger,
    api_logger,
)

from .middleware import (
    setup_request_logging,
    log_database_operation,
    log_ai_operation,
    log_auth_event,
)

from .validators import (
    validate_email,
    validate_username,
    validate_password,
    sanitize_string,
    sanitize_integer,
    require_json,
    require_fields,
    sanitize_payload,
    ValidationError,
)

__all__ = [
    'setup_logger',
    'app_logger',
    'db_logger',
    'ai_logger',
    'auth_logger',
    'chat_logger',
    'api_logger',
    'setup_request_logging',
    'log_database_operation',
    'log_ai_operation',
    'log_auth_event',
    'validate_email',
    'validate_username',
    'validate_password',
    'sanitize_string',
    'sanitize_integer',
    'require_json',
    'require_fields',
    'sanitize_payload',
    'ValidationError',
]
