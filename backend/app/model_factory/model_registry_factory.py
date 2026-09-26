"""Model registry factory for multi-environment registries."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RegistryConfig:
    environment: str
    storage_backend: str
    credentials: Dict[str, str] = field(default_factory=dict)


class ModelRegistryFactory:
    def __init__(self) -> None:
        self._registries: Dict[str, Any] = {}

    def create(self, config: RegistryConfig) -> Any:
        registry_id = f"{config.environment}:{config.storage_backend}"
        if registry_id not in self._registries:
            self._registries[registry_id] = {"config": config, "models": {}}
        return self._registries[registry_id]

    def get(self, environment: str) -> Optional[Any]:
        return self._registries.get(environment)


model_registry_factory = ModelRegistryFactory()
