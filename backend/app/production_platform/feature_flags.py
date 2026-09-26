"""Feature flag management for production features."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FeatureFlag:
    flag_id: str
    name: str
    description: str
    enabled: bool = False
    rules: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FeatureFlagManager:
    def __init__(self) -> None:
        self._flags: Dict[str, FeatureFlag] = {}

    def create_flag(self, name: str, description: str, rules: Optional[List[Dict[str, Any]]] = None) -> FeatureFlag:
        flag_id = uuid.uuid4().hex
        flag = FeatureFlag(flag_id=flag_id, name=name, description=description, rules=rules or [])
        self._flags[flag_id] = flag
        return flag

    def is_enabled(self, flag_id: str, context: Optional[Dict[str, Any]] = None) -> bool:
        flag = self._flags.get(flag_id)
        if not flag:
            return False
        if not flag.rules:
            return flag.enabled
        return any(self._rule_matches(rule, context or {}) for rule in flag.rules)

    def set_enabled(self, flag_id: str, enabled: bool) -> None:
        flag = self._flags.get(flag_id)
        if flag:
            flag.enabled = enabled

    def _rule_matches(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        if rule.get("type") == "user_percent":
            return context.get("user_id", "").endswith(tuple(rule.get("percent", 0) * "0"))
        return True


feature_flag_manager = FeatureFlagManager()
