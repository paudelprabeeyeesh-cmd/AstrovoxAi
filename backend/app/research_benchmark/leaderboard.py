"""Research leaderboard for benchmark ranking."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ResearchEntry:
    rank: int
    model_id: str
    benchmark_id: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResearchLeaderboard:
    def __init__(self) -> None:
        self._entries: List[ResearchEntry] = []

    def submit(self, model_id: str, benchmark_id: str, score: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._entries.append(ResearchEntry(rank=0, model_id=model_id, benchmark_id=benchmark_id, score=score, metadata=metadata or {}))
        self._entries.sort(key=lambda e: e.score, reverse=True)
        for idx, entry in enumerate(self._entries, start=1):
            entry.rank = idx

    def get_leaderboard(self, benchmark_id: str) -> List[ResearchEntry]:
        return [e for e in self._entries if e.benchmark_id == benchmark_id]


research_leaderboard = ResearchLeaderboard()
