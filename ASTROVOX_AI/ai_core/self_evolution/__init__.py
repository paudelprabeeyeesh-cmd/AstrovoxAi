import logging
from typing import Any

logger = logging.getLogger(__name__)


class SelfEvolutionRegistry:
    def __init__(self):
        self.modules: dict[str, Any] = {}

    def register(self, name: str, module: Any) -> None:
        self.modules[name] = module

    def get(self, name: str) -> Any | None:
        return self.modules.get(name)
