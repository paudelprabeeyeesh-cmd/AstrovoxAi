"""Load balancer for Astrovox inference backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Backend:
    """An inference backend."""
    id: str
    host: str
    active: bool = True
    weight: int = 1

    def to_dict(self) -> dict:
        return {"id": self.id, "host": self.host, "active": self.active, "weight": self.weight}


class LoadBalancer:
    """Round-robin / weighted load balancer."""

    def __init__(self):
        self.backends: dict[str, Backend] = {}
        self._index = 0

    def add(self, backend: Backend) -> None:
        self.backends[backend.id] = backend

    def remove(self, backend_id: str) -> bool:
        if backend_id in self.backends:
            del self.backends[backend_id]
            return True
        return False

    def select(self) -> Backend | None:
        active = [b for b in self.backends.values() if b.active]
        if not active:
            return None
        self._index = (self._index + 1) % len(active)
        return active[self._index]

    def select_weighted(self) -> Backend | None:
        active = [(b.weight, b) for b in self.backends.values() if b.active]
        if not active:
            return None
        total = sum(w for w, _ in active)
        import random
        r = random.randint(1, total)
        cum = 0
        for w, b in active:
            cum += w
            if r <= cum:
                return b
        return active[-1][1]

    def get_stats(self) -> dict:
        active = [b for b in self.backends.values() if b.active]
        return {"total": len(self.backends), "active": len(active),
                "standby": len(self.backends) - len(active)}
