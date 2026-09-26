import json
import logging
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        try:
            return json.dumps(log_entry)
        except (TypeError, ValueError):
            return json.dumps(
                {
                    "timestamp": log_entry["timestamp"],
                    "level": log_entry["level"],
                    "message": "Log record contains non-serializable data",
                    "module": log_entry["module"],
                    "function": log_entry["function"],
                }
            )


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
