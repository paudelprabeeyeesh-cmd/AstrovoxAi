import logging
from typing import Any

logger = logging.getLogger(__name__)


class ReasoningRegistry:
    def __init__(self):
        self.engines: dict[str, Any] = {}

    def register(self, name: str, engine: Any) -> None:
        self.engines[name] = engine
        logger.info(f"Registered reasoning engine: {name}")

    def get(self, name: str) -> Any | None:
        return self.engines.get(name)
