"""Structured logging helpers."""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class LogFormatter(json.JSONFormatter):
    def __init__(self, service_name: str = "astrovox-backend"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        extra = getattr(record, "structured_data", None)
        if extra:
            log_entry.update(extra)
        return json.dumps(log_entry, default=str)


def configure_structured_logging(service_name: str = "astrovox-backend", level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(LogFormatter(service_name=service_name))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    if os.getenv("ASTROVOX_LOG_LEVEL"):
        root.setLevel(getattr(logging, os.getenv("ASTROVOX_LOG_LEVEL", "INFO").upper()))


structured_logger = logging.getLogger("astrovox.structured")
