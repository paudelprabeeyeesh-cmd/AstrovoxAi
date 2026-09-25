"""Researcher agent for information gathering."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ResearchResult:
    query: str
    sources: List[str]
    findings: str
    confidence: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ResearcherAgent:
    _results: Dict[str, ResearchResult] = {}

    @classmethod
    def search(cls, query: str) -> ResearchResult:
        findings = f"Research results for: {query}\n\nNo external search configured."
        result = ResearchResult(
            query=query,
            sources=[],
            findings=findings,
            confidence=0.0,
        )
        cls._results[query] = result
        return result

    @classmethod
    def get_result(cls, query: str) -> Optional[ResearchResult]:
        return cls._results.get(query)
