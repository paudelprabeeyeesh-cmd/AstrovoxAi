"""AI logger."""
from __future__ import annotations

import logging
import json
import sys
from datetime import datetime, timezone


class AILogger:
    def __init__(self, name: str = "astrovox.ai"):
        self._logger = logging.getLogger(name)

    def info(self, message: str, **kwargs: Any) -> None:
        self._logger.info(json.dumps({"message": message, "extra": kwargs, "ts": datetime.now(timezone.utc).isoformat()}))

    def error(self, message: str, **kwargs: Any) -> None:
        self._logger.error(json.dumps({"message": message, "extra": kwargs, "ts": datetime.now(timezone.utc).isoformat()}))


ai_logger = AILogger()
