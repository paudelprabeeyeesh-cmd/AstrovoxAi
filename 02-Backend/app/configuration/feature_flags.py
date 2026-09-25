"""Feature flags management."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading

_flags: Dict[str, "FeatureFlag"] = {}
_lock = threading.Lock()


class FlagType(Enum):
    BOOLEAN = "boolean"
    PERCENTAGE = "percentage"
    WHITELIST = "whitelist"


@dataclass
class FeatureFlag:
    key: str
    enabled: bool = False
    description: str = ""
    flag_type: FlagType = FlagType.BOOLEAN
    percentage: int = 0
    whitelist: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class FeatureFlags:
    @classmethod
    def register(cls, flag: FeatureFlag) -> None:
        with _lock:
            _flags[flag.key] = flag

    @classmethod
    def is_enabled(cls, key: str, context: Optional[Dict[str, Any]] = None) -> bool:
        with _lock:
            flag = _flags.get(key)
            if not flag:
                return False
            if not flag.enabled:
                return False
            if flag.flag_type == FlagType.PERCENTAGE:
                user_id = context.get("user_id", "") if context else ""
                return hash(f"{key}:{user_id}") % 100 < flag.percentage
            if flag.flag_type == FlagType.WHITELIST:
                user_id = context.get("user_id", "") if context else ""
                return user_id in flag.whitelist
            return flag.enabled

    @classmethod
    def get(cls, key: str) -> Optional[FeatureFlag]:
        with _lock:
            return _flags.get(key)

    @classmethod
    def set(cls, key: str, enabled: bool) -> None:
        with _lock:
            flag = _flags.get(key)
            if flag:
                flag.enabled = enabled
                flag.updated_at = datetime.utcnow()

    @classmethod
    def list_all(cls) -> List[FeatureFlag]:
        with _lock:
            return list(_flags.values())


FeatureFlags.register(FeatureFlag("new_chat_ui", enabled=False, description="New chat interface"))
FeatureFlags.register(FeatureFlag("beta_features", enabled=False, description="Beta feature access", flag_type=FlagType.PERCENTAGE, percentage=10))
FeatureFlags.register(FeatureFlag("premium_tier", enabled=False, description="Premium tier access", flag_type=FlagType.WHITELIST, whitelist=["user_premium_1", "user_premium_2"]))
