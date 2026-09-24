import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TTLPolicy:
    default_ttl: float
    max_ttl: float
    min_ttl: float


class TTLManager:
    def __init__(self, policy: Optional[TTLPolicy] = None):
        self.policy = policy or TTLPolicy(default_ttl=60.0, max_ttl=3600.0, min_ttl=1.0)
        self._entries: Dict[str, float] = {}

    def register(self, key: str, ttl: Optional[float] = None) -> float:
        resolved = ttl if ttl is not None else self.policy.default_ttl
        resolved = max(self.policy.min_ttl, min(resolved, self.policy.max_ttl))
        self._entries[key] = time.time() + resolved
        return resolved

    def remaining(self, key: str) -> float:
        expiry = self._entries.get(key)
        if expiry is None:
            return 0.0
        remaining = expiry - time.time()
        return max(0.0, remaining)

    def expired(self, key: str) -> bool:
        return self.remaining(key) == 0.0

    def expire(self, key: str) -> bool:
        if key in self._entries:
            del self._entries[key]
            return True
        return False

    def expired_keys(self) -> List[str]:
        return [k for k in list(self._entries.keys()) if self.expired(k)]

    def cleanup(self) -> int:
        expired = self.expired_keys()
        for key in expired:
            del self._entries[key]
        return len(expired)

    def stats(self) -> Dict[str, Any]:
        return {
            "tracked": len(self._entries),
            "default_ttl": self.policy.default_ttl,
            "max_ttl": self.policy.max_ttl,
            "min_ttl": self.policy.min_ttl,
        }
