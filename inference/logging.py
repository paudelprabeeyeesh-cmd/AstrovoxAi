"""Structured logging for inference server."""

import logging
import sys
import os
import json
import time
import uuid
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Context variable for request correlation ID
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(None),
        }

        # Add extra fields
        extra_fields = [
            "endpoint", "method", "status_code", "duration_ms",
            "client_ip", "user_agent", "model", "tokens",
        ]
        for field in extra_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        # Add exception info if present
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_data, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter."""

    def format(self, record: logging.LogRecord) -> str:
        base = f"{self.formatTime(record, self.datefmt)} - {record.levelname:8s} - {record.name} - {record.getMessage()}"
        req_id = request_id_var.get(None)
        if req_id:
            base = f"[{req_id[:8]}] " + base
        return base


def setup_logging(level: str = "INFO", json_format: bool = True):
    """Setup structured logging for the application."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if json_format:
        formatter = StructuredFormatter()
    else:
        formatter = ConsoleFormatter()

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(log_level)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("torch").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)


def log_request(logger: logging.Logger, request_data: Dict[str, Any]):
    """Log an incoming request."""
    logger.info(
        "Request received",
        extra={
            "endpoint": request_data.get("path"),
            "method": request_data.get("method"),
            "client_ip": request_data.get("client_ip"),
            "user_agent": request_data.get("user_agent"),
            "content_length": request_data.get("content_length"),
        },
    )


def log_response(logger: logging.Logger, response_data: Dict[str, Any]):
    """Log an outgoing response."""
    logger.info(
        "Response sent",
        extra={
            "endpoint": response_data.get("path"),
            "method": response_data.get("method"),
            "status_code": response_data.get("status_code"),
            "duration_ms": response_data.get("duration_ms"),
        },
    )


def log_error(logger: logging.Logger, error_data: Dict[str, Any]):
    """Log an error."""
    logger.error(
        error_data.get("message", "Unknown error"),
        exc_info=error_data.get("exc_info"),
        extra={
            "endpoint": error_data.get("endpoint"),
            "method": error_data.get("method"),
        },
    )


def log_model_event(logger: logging.Logger, event: str, details: Dict[str, Any]):
    """Log a model lifecycle event."""
    logger.info(
        f"Model event: {event}",
        extra={"model_event": event, "model_details": details},
    )
