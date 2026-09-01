"""Security Level 3 — Zero Trust, hardware security, runtime protection."""

import time
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SecurityPolicy:
    """A security policy."""
    id: str
    name: str
    policy_type: str
    enabled: bool = True
    created_at: float = 0.0

    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()


class ZeroTrustManager:
    """Zero Trust security manager."""

    def __init__(self):
        self._policies: dict[str, SecurityPolicy] = {}
        self._trust_scores: dict = {}

    def add_policy(self, name: str, policy_type: str) -> SecurityPolicy:
        import secrets
        policy = SecurityPolicy(
            id=secrets.token_hex(8),
            name=name,
            policy_type=policy_type,
        )
        self._policies[policy.id] = policy
        return policy

    def evaluate_trust(self, user_id: str, device_id: str, context: dict) -> float:
        """Evaluate trust score (0-100)."""
        score = 100.0

        if context.get("new_device"):
            score -= 20
        if context.get("unusual_location"):
            score -= 30
        if context.get("failed_attempts", 0) > 0:
            score -= context["failed_attempts"] * 10

        self._trust_scores[user_id] = max(0, score)
        return max(0, score)

    def is_trusted(self, user_id: str, threshold: float = 50.0) -> bool:
        return self._trust_scores.get(user_id, 0) >= threshold


zero_trust = ZeroTrustManager()
