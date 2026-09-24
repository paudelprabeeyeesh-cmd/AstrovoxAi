import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class VersionVector:
    _clock: Dict[str, int] = field(default_factory=dict)

    def increment(self, node_id: str) -> int:
        current = self._clock.get(node_id, 0) + 1
        self._clock[node_id] = current
        return current

    def merge(self, other: "VersionVector") -> None:
        for node_id, version in other._clock.items():
            self._clock[node_id] = max(self._clock.get(node_id, 0), version)

    def compare(self, other: "VersionVector") -> bool:
        if not self._clock:
            return True
        for node_id, version in self._clock.items():
            if other._clock.get(node_id, 0) < version:
                return False
        return True

    def to_dict(self) -> Dict[str, int]:
        return dict(self._clock)

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "VersionVector":
        instance = cls()
        instance._clock = dict(data)
        return instance

    def copy(self) -> "VersionVector":
        return VersionVector.from_dict(self._clock)
