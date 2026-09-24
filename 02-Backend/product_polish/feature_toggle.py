"""
feature_toggle - product_polish

Manage feature flags with environment-specific overrides and audit logging.
"""

from __future__ import annotations

import copy
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FeatureToggle:
    key: str
    enabled: bool
    environment: str = "default"
    description: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.updated_at:
            self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "enabled": self.enabled,
            "environment": self.environment,
            "description": self.description,
            "updated_at": self.updated_at,
        }


class FeatureToggleStore:
    def __init__(self):
        self._toggles: Dict[str, FeatureToggle] = {}
        self._lock = threading.Lock()

    def set(self, key: str, enabled: bool, environment: str = "default", description: str = "") -> FeatureToggle:
        with self._lock:
            existing = self._toggles.get(key)
            toggle = FeatureToggle(
                key=key,
                enabled=enabled,
                environment=environment,
                description=description or (existing.description if existing else ""),
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            self._toggles[key] = toggle
            logger.info("Set feature toggle %s=%s (%s)", key, enabled, environment)
            return toggle

    def get(self, key: str, environment: str = "default") -> Optional[FeatureToggle]:
        with self._lock:
            toggle = self._toggles.get(key)
            if toggle is None:
                return None
            if toggle.environment != environment:
                generic = self._toggles.get(key)
                if generic and generic.environment == "default":
                    return generic
                return None
            return toggle

    def is_enabled(self, key: str, environment: str = "default", default: bool = False) -> bool:
        toggle = self.get(key, environment)
        if toggle is None:
            return default
        return toggle.enabled

    def list_toggles(self, environment: Optional[str] = None) -> List[FeatureToggle]:
        with self._lock:
            toggles = list(self._toggles.values())
        if environment is not None:
            toggles = [t for t in toggles if t.environment == environment]
        return sorted(toggles, key=lambda t: t.key)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._toggles:
                del self._toggles[key]
                return True
            return False
