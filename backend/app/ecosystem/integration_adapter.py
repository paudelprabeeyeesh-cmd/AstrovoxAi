"""Integration adapters for third-party services."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class IntegrationConfig:
    integration_id: str
    provider: str
    credentials: Dict[str, str] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)


class IntegrationAdapter:
    def __init__(self, config: IntegrationConfig) -> None:
        self.config = config

    async def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("sending integration event to %s", self.config.provider)
        return {"status": "sent", "provider": self.config.provider}

    async def receive(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("receiving integration event from %s", self.config.provider)
        return {"status": "received", "provider": self.config.provider}


class IntegrationHub:
    def __init__(self) -> None:
        self._adapters: Dict[str, IntegrationAdapter] = {}

    def register(self, config: IntegrationConfig) -> IntegrationAdapter:
        adapter = IntegrationAdapter(config)
        self._adapters[config.integration_id] = adapter
        return adapter

    def get(self, integration_id: str) -> Optional[IntegrationAdapter]:
        return self._adapters.get(integration_id)


integration_hub = IntegrationHub()
