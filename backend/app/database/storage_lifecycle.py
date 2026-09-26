"""Storage lifecycle management."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StorageTier(str, Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    ARCHIVE = "archive"


@dataclass
class LifecyclePolicy:
    table_name: str
    tier: StorageTier
    retention_days: int
    transition_after_days: int = 0


@dataclass
class StorageObject:
    key: str
    size_bytes: int
    created_at: datetime
    last_accessed: datetime
    tier: StorageTier
    tags: Dict[str, str] = field(default_factory=dict)


class StorageLifecycleManager:
    def __init__(self):
        self._objects: Dict[str, StorageObject] = {}
        self._policies: Dict[str, LifecyclePolicy] = {}

    def register_policy(self, policy: LifecyclePolicy) -> None:
        self._policies[policy.table_name] = policy

    def register_object(self, obj: StorageObject) -> None:
        self._objects[obj.key] = obj

    def apply_lifecycle(self, now: Optional[datetime] = None) -> List[str]:
        now = now or datetime.utcnow()
        transitions = []
        for key, obj in list(self._objects.items()):
            policy = self._policies.get(obj.tags.get("table", ""))
            if policy is None:
                continue
            age = (now - obj.created_at).days
            if age >= policy.retention_days:
                self._objects.pop(key, None)
                transitions.append(f"expired:{key}")
                continue
            if age >= policy.transition_after_days and obj.tier != policy.tier:
                obj.tier = policy.tier
                transitions.append(f"{key}:{policy.tier}")
        logger.info("Applied lifecycle to %s objects", len(transitions))
        return transitions

    def estimate_storage(self, tier: Optional[StorageTier] = None) -> Dict[str, Any]:
        objects = list(self._objects.values())
        if tier is not None:
            objects = [o for o in objects if o.tier == tier]
        total_bytes = sum(o.size_bytes for o in objects)
        return {
            "object_count": len(objects),
            "total_bytes": total_bytes,
            "tier": tier.value if tier else "all",
        }
