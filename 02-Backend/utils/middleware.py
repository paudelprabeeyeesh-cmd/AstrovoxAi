"""
Request Logging & Tracking Middleware
Logs all HTTP requests, responses, and errors with performance metrics.
"""

import os
import time
import logging
from datetime import datetime
from typing import Callable, Any, Optional
from flask import Flask, request, g

logger = logging.getLogger("astravox.middleware")


def _safe_get_json() -> dict:
    """Safely attempt to get request JSON payload."""
    try:
        return request.get_json() or {}
    except Exception:
        return {}


def _sanitize_payload(data: dict, sensitive_keys: list = None) -> dict:
    """Remove sensitive information from logged data."""
    if sensitive_keys is None:
        sensitive_keys = ["password", "api_key", "secret", "token"]
    
    sanitized = {}
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = "***REDACTED***"
        else:
            sanitized[key] = value
    return sanitized


def setup_request_logging(app: Flask) -> None:
    """
    Register request/response logging middleware.
    
    Logs:
    - Request method, path, and parameters
    - Response status code and timing
    - Errors and exceptions
    - Performance metrics
    """
    
    @app.before_request
    def before_request():
        """Called before each request."""
        g.start_time = time.time()
        
        # Log request
        method = request.method
        path = request.path
        remote_addr = request.remote_addr
        user_agent = request.headers.get("User-Agent", "Unknown")[:100]
        
        logger.info(
            f"→ {method} {path} | From: {remote_addr} | UA: {user_agent}"
        )
        
        # Log request body for POST/PUT/PATCH
        if method in ["POST", "PUT", "PATCH"]:
            try:
                payload = _safe_get_json()
                sanitized = _sanitize_payload(payload)
                logger.debug(f"  Request payload: {sanitized}")
            except Exception as e:
                logger.debug(f"  Could not parse request body: {e}")
    
    @app.after_request
    def after_request(response):
        """Called after each request."""
        elapsed = time.time() - g.get("start_time", time.time())
        
        method = request.method
        path = request.path
        status = response.status_code
        
        # Log response
        status_emoji = "✅" if status < 400 else "⚠️" if status < 500 else "❌"
        logger.info(
            f"← {status_emoji} {status} {method} {path} | Time: {elapsed:.3f}s"
        )
        
        # Log response body for errors
        if status >= 400:
            try:
                if response.is_json:
                    logger.warning(f"  Response: {response.get_json()}")
            except Exception:
                pass
        
        return response
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Global exception handler."""
        logger.exception(f"❌ EXCEPTION: {type(error).__name__}: {error}")
        
        # Return error response
        return {
            "status": "ERROR",
            "error": str(error),
            "detail": "Internal server error"
        }, 500


def log_database_operation(operation: str, table: str, affected_rows: int = 0) -> None:
    """Log database operations."""
    db_logger = logging.getLogger("astravox.database")
    db_logger.debug(f"{operation.upper()} {table} | Rows affected: {affected_rows}")


def log_ai_operation(operation: str, model: str, tokens: int = 0, latency: float = 0.0) -> None:
    """Log AI/LLM operations."""
    ai_logger = logging.getLogger("astravox.ai")
    msg = f"{operation} | Model: {model}"
    if tokens:
        msg += f" | Tokens: {tokens}"
    if latency:
        msg += f" | Latency: {latency:.2f}s"
    ai_logger.info(msg)


def log_auth_event(event: str, user_id: Optional[str] = None, success: bool = True) -> None:
    """Log authentication events."""
    auth_logger = logging.getLogger("astravox.auth")
    status = "✅" if success else "❌"
    msg = f"{status} {event}"
    if user_id:
        msg += f" | User: {user_id}"
    auth_logger.info(msg)
