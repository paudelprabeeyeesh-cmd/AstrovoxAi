"""AI version management."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIVersionPolicy:
    current_version: str
    supported_versions: List[str]
    deprecation_window_days: int = 90


class AIVersionManager:
    def __init__(self) -> None:
        self._policies: Dict[str, AIVersionPolicy] = {}

    def register_policy(self, service: str, policy: AIVersionPolicy) -> None:
        self._policies[service] = policy

    def is_supported(self, service: str, version: str) -> bool:
        policy = self._policies.get(service)
        return bool(policy and version in policy.supported_versions)


ai_version_manager = AIVersionManager()
