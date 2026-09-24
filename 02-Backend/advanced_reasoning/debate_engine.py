from dataclasses import dataclass
from typing import List, Optional
import numpy as np


@dataclass
class Perspective:
    id: str
    name: str
    stance: str
    arguments: List[str]
    evidence: List[str]
    confidence: float = 0.8


@dataclass
class DebateResult:
    perspectives: List[Perspective]
    consensus: Optional[str]
    disagreement_areas: List[str]
    synthesis: str
    confidence: float = 0.0


class DebateEngine:
    def __init__(self, min_perspectives: int = 2, max_perspectives: int = 5):
        self.min_perspectives = min_perspectives
        self.max_perspectives = max_perspectives

    def analyze(self, topic: str, perspectives: List[Perspective]) -> DebateResult:
        if len(perspectives) < self.min_perspectives:
            raise ValueError(f"At least {self.min_perspectives} perspectives required")
        trimmed = perspectives[: self.max_perspectives]
        consensus = self._build_consensus(trimmed)
        disagreements = self._find_disagreements(trimmed)
        synthesis = self._synthesize(trimmed, consensus, disagreements)
        confidence = self._compute_confidence(trimmed, consensus)
        return DebateResult(
            perspectives=trimmed,
            consensus=consensus,
            disagreement_areas=disagreements,
            synthesis=synthesis,
            confidence=confidence,
        )

    def _build_consensus(self, perspectives: List[Perspective]) -> Optional[str]:
        stances = [p.stance for p in perspectives]
        unique_stances = list(set(stances))
        if len(unique_stances) == 1:
            return unique_stances[0]
        confs = [p.confidence for p in perspectives]
        best_idx = int(np.argmax(confs))
        return f"Mixed: {stances[best_idx]} (leading)"

    def _find_disagreements(self, perspectives: List[Perspective]) -> List[str]:
        all_args = [set(p.arguments) for p in perspectives]
        if not all_args:
            return []
        common = set.intersection(*all_args)
        disagreements = []
        for p in perspectives:
            diff = set(p.arguments) - common
            if diff:
                disagreements.append(f"{p.name} differs on: {', '.join(list(diff)[:3])}")
        return disagreements

    def _synthesize(self, perspectives: List[Perspective], consensus: Optional[str], disagreements: List[str]) -> str:
        parts = []
        if consensus:
            parts.append(f"Consensus: {consensus}")
        if disagreements:
            parts.append("Disagreements: " + "; ".join(disagreements[:3]))
        strengths = [f"{p.name} ({len(p.evidence)} evidence items)" for p in perspectives]
        parts.append("Perspectives: " + ", ".join(strengths))
        return " | ".join(parts)

    def _compute_confidence(self, perspectives: List[Perspective], consensus: Optional[str]) -> float:
        if not perspectives:
            return 0.0
        confs = [p.confidence for p in perspectives]
        base = float(np.mean(confs))
        if consensus and len(set(p.stance for p in perspectives)) == 1:
            base = min(1.0, base + 0.1)
        return base
