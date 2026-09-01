"""Product Engineering — UX research, accessibility, analytics, feature flags."""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FeatureFlag:
    """A feature flag."""
    name: str
    enabled: bool
    description: str
    created_at: float = 0.0

    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()


class FeatureFlagManager:
    """Manage feature flags."""

    def __init__(self):
        self._flags: dict[str, FeatureFlag] = {}

    def register(self, name: str, enabled: bool, description: str = ""):
        """Register a feature flag."""
        self._flags[name] = FeatureFlag(name, enabled, description)

    def is_enabled(self, name: str) -> bool:
        """Check if a feature is enabled."""
        flag = self._flags.get(name)
        return flag.enabled if flag else False

    def enable(self, name: str):
        """Enable a feature."""
        if name in self._flags:
            self._flags[name].enabled = True

    def disable(self, name: str):
        """Disable a feature."""
        if name in self._flags:
            self._flags[name].enabled = False

    def list_flags(self) -> list[dict]:
        """List all feature flags."""
        return [
            {
                "name": f.name,
                "enabled": f.enabled,
                "description": f.description,
            }
            for f in self._flags.values()
        ]


class UserAnalytics:
    """Track user analytics."""

    def __init__(self):
        self._events: list = []

    def track(self, user_id: str, event: str, properties: dict = None):
        """Track an event."""
        self._events.append({
            "user_id": user_id,
            "event": event,
            "properties": properties or {},
            "timestamp": time.time(),
        })

    def get_user_events(self, user_id: str) -> list:
        """Get events for a user."""
        return [e for e in self._events if e["user_id"] == user_id]

    def get_event_count(self, event: str) -> int:
        """Get count of a specific event."""
        return len([e for e in self._events if e["event"] == event])


class ABTestManager:
    """Manage A/B tests."""

    def __init__(self):
        self._tests: dict = {}

    def create_test(self, name: str, variants: list[str], traffic_split: list[float] = None):
        """Create an A/B test."""
        if traffic_split is None:
            traffic_split = [1.0 / len(variants)] * len(variants)

        self._tests[name] = {
            "variants": variants,
            "traffic_split": traffic_split,
            "results": {v: {"impressions": 0, "conversions": 0} for v in variants},
        }

    def get_variant(self, test_name: str, user_id: str) -> str:
        """Get variant for a user."""
        test = self._tests.get(test_name)
        if not test:
            return "control"

        import hashlib
        hash_val = int(hashlib.md5(f"{test_name}:{user_id}".encode()).hexdigest(), 16)
        bucket = hash_val % 100 / 100.0

        cumulative = 0
        for variant, split in zip(test["variants"], test["traffic_split"]):
            cumulative += split
            if bucket < cumulative:
                test["results"][variant]["impressions"] += 1
                return variant

        return test["variants"][0]

    def record_conversion(self, test_name: str, variant: str):
        """Record a conversion."""
        test = self._tests.get(test_name)
        if test and variant in test["results"]:
            test["results"][variant]["conversions"] += 1

    def get_results(self, test_name: str) -> dict:
        """Get test results."""
        return self._tests.get(test_name, {})


feature_flags = FeatureFlagManager()
user_analytics = UserAnalytics()
ab_test_manager = ABTestManager()
