"""Platform version management."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class VersionPolicy:
    current_version: str
    supported_versions: List[str]
    deprecation_window_days: int = 90


class VersionManager:
    def __init__(self) -> None:
        self._policies: Dict[str, VersionPolicy] = {}

    def register_policy(self, service: str, policy: VersionPolicy) -> None:
        self._policies[service] = policy

    def is_supported(self, service: str, version: str) -> bool:
        policy = self._policies.get(service)
        return bool(policy and version in policy.supported_versions)

    def get_policy(self, service: str) -> Optional[VersionPolicy]:
        return self._policies.get(service)


version_manager = VersionManager()
