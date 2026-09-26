"""AI model registry factory."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIRegistryConfig:
    environment: str
    backend: str
    credentials: Dict[str, str] = field(default_factory=dict)


class AIModelRegistryFactory:
    def __init__(self) -> None:
        self._registries: Dict[str, Any] = {}

    def create(self, config: AIRegistryConfig) -> Any:
        key = f"{config.environment}:{config.backend}"
        if key not in self._registries:
            self._registries[key] = {"config": config}
        return self._registries[key]


ai_model_registry_factory = AIModelRegistryFactory()
