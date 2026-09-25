"""Enhanced structured logging formatter with JSON output, context propagation, and log enrichment."""

from __future__ import annotations

import logging
import json
import sys
import os
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List


class JSONFormatter(logging.Formatter):
    """Production-grade JSON log formatter with rich context support."""

    def __init__(self, service_name: str = "astrovoxai", version: str = "1.0.0"):
        super().__init__()
        self._service_name = service_name
        self._version = version

    def format(self, record: logging.LogRecord) -> str:
        now = datetime.now(timezone.utc)
        log_entry: Dict[str, Any] = {
            "timestamp": now.isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": {
                "name": self._service_name,
                "version": self._version,
            },
            "location": {
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "file": record.pathname,
            },
        }

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        for field in ("request_id", "correlation_id", "trace_id", "span_id",
                       "user_id", "duration_ms", "method", "path", "status_code",
                       "client_ip", "user_agent", "model", "tokens"):
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)

        if record.args and isinstance(record.args, dict):
            log_entry["context"] = record.args

        extra_data: Dict[str, Any] = {}
        reserved = {
            "name", "msg", "args", "created", "relativeCreated", "exc_info",
            "exc_text", "stack_info", "lineno", "funcName", "filename",
            "module", "pathname", "levelname", "levelno", "msecs", "thread",
            "threadName", "process", "processName", "taskName", "message",
            "request_id", "correlation_id", "trace_id", "span_id", "user_id",
            "duration_ms", "method", "path", "status_code", "client_ip",
            "user_agent", "model", "tokens", "context",
        }
        for key, value in record.__dict__.items():
            if key not in reserved and not key.startswith("_"):
                try:
                    json.dumps(value)
                    extra_data[key] = value
                except (TypeError, ValueError):
                    extra_data[key] = str(value)

        if extra_data:
            log_entry["extra"] = extra_data

        return json.dumps(log_entry, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter with color-coded levels."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
        "RESET": "\033[0m",
    }

    def __init__(self, service_name: str = "astrovoxai"):
        super().__init__()
        self._service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]
        ts = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        base = f"{color}[{ts}] [{record.levelname}] {self._service_name}: {record.getMessage()}{reset}"

        cid = getattr(record, "correlation_id", None)
        if cid:
            base += f" [cid={cid}]"

        if record.exc_info and record.exc_info[0]:
            base += "\n" + self.formatException(record.exc_info)

        return base


class LogEnricher:
    """Enriches log records with contextual information."""

    @staticmethod
    def add_context(record: logging.LogRecord, **context: Any) -> logging.LogRecord:
        for key, value in context.items():
            setattr(record, key, value)
        return record

    @staticmethod
    def enrich_request(record: logging.LogRecord, request: Any) -> logging.LogRecord:
        try:
            record.method = request.method
            record.path = str(request.url.path)
            record.client_ip = request.client.host if request.client else "unknown"
            record.user_agent = request.headers.get("user-agent", "")
            record.status_code = getattr(request.state, "status_code", None)
        except Exception:
            pass
        return record


def setup_logging(
    service_name: str = "astrovoxai",
    service_version: str = "1.0.0",
    log_level: str = "INFO",
    log_format: str = "json",
) -> logging.Logger:
    """Configure structured logging for production.

    Args:
        service_name: Service name for log context.
        service_version: Service version for log context.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: Output format ('json' or 'console').

    Returns:
        Configured root logger instance.
    """
    root_logger = logging.getLogger("astravox")
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if root_logger.handlers:
        root_logger.handlers.clear()

    if log_format == "json":
        formatter = JSONFormatter(service_name=service_name, version=service_version)
    else:
        formatter = ConsoleFormatter(service_name=service_name)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    log_dir = os.getenv("LOG_DIR", "/tmp/astravox-logs")
    os.makedirs(log_dir, exist_ok=True)
    file_path = os.path.join(log_dir, f"{service_name}.log")
    file_handler = logging.handlers.RotatingFileHandler(
        file_path, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    file_handler.setFormatter(JSONFormatter(service_name=service_name, version=service_version))
    root_logger.addHandler(file_handler)

    root_logger.info("Logging initialized", extra={
        "service_name": service_name,
        "service_version": service_version,
        "log_level": log_level,
        "log_format": log_format,
    })
    return root_logger


logger = logging.getLogger("astravox")
