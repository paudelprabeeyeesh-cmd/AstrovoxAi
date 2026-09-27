"""AI research leaderboard."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIResearchEntry:
    rank: int
    model_id: str
    benchmark_id: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class AIResearchLeaderboard:
    def __init__(self) -> None:
        self._entries: List[AIResearchEntry] = []

    def submit(self, model_id: str, benchmark_id: str, score: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._entries.append(AIResearchEntry(rank=0, model_id=model_id, benchmark_id=benchmark_id, score=score, metadata=metadata or {}))
        self._entries.sort(key=lambda e: e.score, reverse=True)
        for idx, entry in enumerate(self._entries, start=1):
            entry.rank = idx

    def get_leaderboard(self, benchmark_id: str) -> List[AIResearchEntry]:
        return [e for e in self._entries if e.benchmark_id == benchmark_id]


ai_research_leaderboard = AIResearchLeaderboard()
