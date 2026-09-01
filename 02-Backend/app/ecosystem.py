"""AI Ecosystem — GitHub, Google Workspace, Slack, Discord integrations."""

import time
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Integration:
    """An external integration."""
    id: str
    name: str
    provider: str
    is_connected: bool = False
    config: dict = None
    connected_at: float = 0.0

    def __post_init__(self):
        if self.config is None:
            self.config = {}


class EcosystemManager:
    """Manage external integrations."""

    def __init__(self):
        self._integrations: dict[str, Integration] = {}

    def register(self, name: str, provider: str, config: dict = None) -> Integration:
        """Register an integration."""
        import secrets
        integration = Integration(
            id=secrets.token_hex(8),
            name=name,
            provider=provider,
            config=config or {},
        )
        self._integrations[integration.id] = integration
        return integration

    def connect(self, integration_id: str):
        integration = self._integrations.get(integration_id)
        if integration:
            integration.is_connected = True
            integration.connected_at = time.time()

    def disconnect(self, integration_id: str):
        integration = self._integrations.get(integration_id)
        if integration:
            integration.is_connected = False

    def get_integrations(self, provider: str = None) -> list:
        integrations = list(self._integrations.values())
        if provider:
            integrations = [i for i in integrations if i.provider == provider]
        return integrations


ecosystem_manager = EcosystemManager()
