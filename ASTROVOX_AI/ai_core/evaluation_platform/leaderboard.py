"""AI leaderboard."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AILeaderboardEntry:
    rank: int
    model_id: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class AILeaderboard:
    def __init__(self, name: str) -> None:
        self.name = name
        self._entries: Dict[str, AILeaderboardEntry] = {}

    def submit(self, model_id: str, score: float, metadata: Optional[Dict[str, Any]] = None) -> AILeaderboardEntry:
        entry = AILeaderboardEntry(rank=0, model_id=model_id, score=score, metadata=metadata or {})
        self._entries[model_id] = entry
        self._recompute()
        return entry

    def _recompute(self) -> None:
        sorted_entries = sorted(self._entries.values(), key=lambda e: e.score, reverse=True)
        for idx, entry in enumerate(sorted_entries, start=1):
            entry.rank = idx

    def get_top(self, n: int = 10) -> List[AILeaderboardEntry]:
        return sorted(self._entries.values(), key=lambda e: e.score, reverse=True)[:n]


ai_leaderboard = AILeaderboard("astrovox-ai")
