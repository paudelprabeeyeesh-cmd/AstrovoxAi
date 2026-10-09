from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FrozenValue:
    name: str
    value: Any
    locked_at: float
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class ValueLock:
    def __init__(self, max_locks: int = 100):
        self.max_locks = max_locks
        self._locked_values: Dict[str, FrozenValue] = {}
        self._change_log: List[Dict] = []

    def lock_value(self, name: str, value: Any, reason: str = "safety") -> bool:
        if name in self._locked_values:
            return False
        if len(self._locked_values) >= self.max_locks:
            return False
        frozen = FrozenValue(
            name=name,
            value=value,
            locked_at=self._now(),
            reason=reason,
        )
        self._locked_values[name] = frozen
        self._change_log.append({"action": "lock", "name": name, "reason": reason})
        return True

    def unlock_value(self, name: str, requester: str = "human") -> bool:
        if name not in self._locked_values:
            return False
        del self._locked_values[name]
        self._change_log.append({"action": "unlock", "name": name, "requester": requester})
        return True

    def get_locked_value(self, name: str) -> Optional[Any]:
        if name not in self._locked_values:
            return None
        return self._locked_values[name].value

    def is_locked(self, name: str) -> bool:
        return name in self._locked_values

    def enforce_locks(self, proposed_changes: Dict[str, Any]) -> Dict[str, Any]:
        blocked = {}
        allowed = {}
        for name, value in proposed_changes.items():
            if self.is_locked(name):
                blocked[name] = {"proposed": value, "locked": self._locked_values[name].value}
            else:
                allowed[name] = value
        if blocked:
            self._change_log.append({"action": "enforce", "blocked": list(blocked.keys())})
        return {"blocked": blocked, "allowed": allowed}

    def get_lock_summary(self) -> Dict[str, Any]:
        return {
            "total_locked": len(self._locked_values),
            "names": list(self._locked_values.keys()),
            "recent_actions": self._change_log[-10:],
        }

    def _now(self) -> float:
        import time
        return time.time()
