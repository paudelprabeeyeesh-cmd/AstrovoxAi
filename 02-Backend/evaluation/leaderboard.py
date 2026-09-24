import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import time

logger = logging.getLogger(__name__)


@dataclass
class LeaderboardEntry:
    rank: int
    name: str
    score: float
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


class Leaderboard:
    def __init__(self, name: str, max_size: int = 100):
        self.name = name
        self.max_size = max_size
        self._entries: Dict[str, LeaderboardEntry] = {}

    def submit(self, name: str, score: float, metadata: Optional[dict] = None) -> LeaderboardEntry:
        existing = self._entries.get(name)
        if existing is not None and score <= existing.score:
            return existing

        entry = LeaderboardEntry(
            rank=0,
            name=name,
            score=score,
            metadata=metadata or {},
        )
        self._entries[name] = entry
        self._update_ranks()
        self._enforce_size()
        return entry

    def _update_ranks(self) -> None:
        sorted_entries = sorted(self._entries.values(), key=lambda e: e.score, reverse=True)
        for i, entry in enumerate(sorted_entries):
            entry.rank = i + 1

    def _enforce_size(self) -> None:
        while len(self._entries) > self.max_size:
            lowest = min(self._entries.values(), key=lambda e: e.score)
            del self._entries[lowest.name]
            self._update_ranks()

    def top(self, n: int = 10) -> List[LeaderboardEntry]:
        sorted_entries = sorted(self._entries.values(), key=lambda e: e.score, reverse=True)
        return sorted_entries[:n]

    def get(self, name: str) -> Optional[LeaderboardEntry]:
        return self._entries.get(name)

    def ranking(self) -> List[LeaderboardEntry]:
        return self.top(n=len(self._entries))

    def size(self) -> int:
        return len(self._entries)
