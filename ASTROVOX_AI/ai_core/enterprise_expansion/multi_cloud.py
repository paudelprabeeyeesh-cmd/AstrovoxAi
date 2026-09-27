"""AI multi-cloud manager."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AICloudProvider:
    provider_id: str
    name: str
    regions: List[str] = field(default_factory=list)
    credentials: Dict[str, str] = field(default_factory=dict)


class AIMultiCloudManager:
    def __init__(self) -> None:
        self._providers: Dict[str, AICloudProvider] = {}

    def register_provider(self, provider: AICloudProvider) -> None:
        self._providers[provider.provider_id] = provider

    def get_provider(self, provider_id: str) -> Optional[AICloudProvider]:
        return self._providers.get(provider_id)


ai_multi_cloud_manager = AIMultiCloudManager()
