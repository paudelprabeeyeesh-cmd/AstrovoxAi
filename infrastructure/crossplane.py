"""Crossplane provider management."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CrossplaneProvider:
    provider_id: str
    name: str
    package: str
    config: Dict[str, Any] = field(default_factory=dict)


class CrossplaneManager:
    def __init__(self) -> None:
        self._providers: Dict[str, CrossplaneProvider] = {}

    def register_provider(self, provider: CrossplaneProvider) -> None:
        self._providers[provider.provider_id] = provider


crossplane_manager = CrossplaneManager()
