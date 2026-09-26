"""Leaderboard for ranking models and experiments."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LeaderboardEntry:
    rank: int
    model_id: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class Leaderboard:
    def __init__(self, name: str, metric: str = "score", max_entries: int = 100):
        self.name = name
        self.metric = metric
        self.max_entries = max_entries
        self._entries: Dict[str, LeaderboardEntry] = {}

    def submit(self, model_id: str, score: float, metadata: Optional[Dict[str, Any]] = None) -> LeaderboardEntry:
        self._entries[model_id] = LeaderboardEntry(rank=0, model_id=model_id, score=score, metadata=metadata or {})
        self._recompute_ranks()
        return self._entries[model_id]

    def get_top(self, n: int = 10) -> List[LeaderboardEntry]:
        return sorted(self._entries.values(), key=lambda e: e.score, reverse=True)[:n]

    def get_entry(self, model_id: str) -> Optional[LeaderboardEntry]:
        return self._entries.get(model_id)

    def _recompute_ranks(self) -> None:
        sorted_entries = sorted(self._entries.values(), key=lambda e: e.score, reverse=True)[: self.max_entries]
        for idx, entry in enumerate(sorted_entries, start=1):
            entry.rank = idx


leaderboard = Leaderboard("astrovox-default")
