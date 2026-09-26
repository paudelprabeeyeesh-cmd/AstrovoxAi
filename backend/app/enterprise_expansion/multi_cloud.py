"""Multi-cloud management."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CloudProvider:
    provider_id: str
    name: str
    regions: List[str] = field(default_factory=list)
    credentials: Dict[str, str] = field(default_factory=dict)


class MultiCloudManager:
    def __init__(self) -> None:
        self._providers: Dict[str, CloudProvider] = {}

    def register_provider(self, provider: CloudProvider) -> None:
        self._providers[provider.provider_id] = provider

    def get_provider(self, provider_id: str) -> Optional[CloudProvider]:
        return self._providers.get(provider_id)


multi_cloud_manager = MultiCloudManager()
