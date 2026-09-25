"""Historical state diffing.

Provides:
- State diff computation
- Historical diff tracking
- Semantic diffing
- Diff visualization data
- Diff statistics
"""

from __future__ import annotations

import copy
import difflib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class DiffLevel(Enum):
    """Diff granularity level."""

    GRANULAR = "granular"
    FIELD = "field"
    SEMANTIC = "semantic"
    STRUCTURAL = "structural"


@dataclass
class DiffResult:
    """State diff result."""

    diff_id: str
    state_a: Dict[str, Any]
    state_b: Dict[str, Any]
    level: DiffLevel
    additions: List[Dict[str, Any]] = field(default_factory=list)
    deletions: List[Dict[str, Any]] = field(default_factory=list)
    modifications: List[Dict[str, Any]] = field(default_factory=list)
    unchanged: List[Dict[str, Any]] = field(default_factory=list)
    score: float = 0.0
    similarity: float = 100.0
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "diff_id": self.diff_id,
            "additions": self.additions,
            "deletions": self.deletions,
            "modifications": self.modifications,
            "unchanged": self.unchanged,
            "score": self.score,
            "similarity": self.similarity,
            "issued_at": self.issued_at.isoformat(),
        }

    def summary(self) -> str:
        return (
            f"additions={len(self.additions)} "
            f"deletions={len(self.deletions)} "
            f"modifications={len(self.modifications)} "
            f"unchanged={len(self.unchanged)} "
            f"similarity={self.similarity:.1f}%"
        )


class HistoricalDiff:
    """Historical state diff tracking.

    Provides:
    - Sequential diff tracking
    - Change detection
    - Historical trend analysis
    - Diff visualization
    """

    def __init__(self, state_a: Dict[str, Any], state_b: Dict[str, Any], issued_at: Optional[datetime] = None):
        self.state_a = copy.deepcopy(state_a)
        self.state_b = copy.deepcopy(state_b)
        self.issued_at = issued_at or datetime.now(timezone.utc)
        self._lock = False

    def granular_diff(self) -> DiffResult:
        return self._compute_diff(DiffLevel.GRANULAR)

    def field_diff(self) -> DiffResult:
        return self._compute_diff(DiffLevel.FIELD)

    def _compute_diff(self, level: DiffLevel) -> DiffResult:
        import uuid

        result = self._compute_field_diff()
        return DiffResult(
            diff_id=str(uuid.uuid4()),
            state_a=copy.deepcopy(self.state_a),
            state_b=copy.deepcopy(self.state_b),
            level=level,
            additions=result["additions"],
            deletions=result["deletions"],
            modifications=result["modifications"],
            unchanged=result["unchanged"],
            score=result["score"],
            similarity=result["similarity"],
        )

    def _compute_field_diff(self) -> Dict[str, Any]:
        keys = set(self.state_a.keys()) | set(self.state_b.keys())
        additions, deletions, modifications, unchanged = [], [], [], []
        score = 0
        for key in keys:
            if key in self.state_a and key in self.state_b:
                a, b = self.state_a[key], self.state_b[key]
                if a == b:
                    unchanged.append({"field": key, "value": a})
                else:
                    modifications.append({"field": key, "value_a": a, "value_b": b})
                    score += 1
            elif key in self.state_b:
                additions.append({"field": key, "value": self.state_b[key]})
                score += 1
            elif key in self.state_a:
                deletions.append({"field": key, "value": self.state_a[key]})
                score += 1
        total = len(additions) + len(deletions) + len(modifications) + len(unchanged)
        similarity = ((len(unchanged) / total) * 100) if total else 100.0
        return {"additions": additions, "deletions": deletions, "modifications": modifications, "unchanged": unchanged, "score": score, "similarity": similarity}

    def to_json_diff(self) -> str:
        return json.dumps(self._compute_field_diff(), indent=2)

    def unified_diff(self) -> str:
        a_str = json.dumps(self.state_a, indent=2, sort_keys=True)
        b_str = json.dumps(self.state_b, indent=2, sort_keys=True)
        lines = difflib.unified_diff(
            a_str.splitlines(keepends=True),
            b_str.splitlines(keepends=True),
            fromfile="state_a",
            tofile="state_b",
        )
        return "".join(lines)

    def __repr__(self) -> str:
        return f"HistoricalDiff(score={self._compute_field_diff()['score']}, similarity={self._compute_field_diff()['similarity']:.1f}%)"


class StateDiffer:
    """State differ for point-in-time comparisons.

    Provides:
    - Point-in-time diffs
    - Semantic diff analysis
    - Diff visualization data
    - Diff statistics
    """

    def __init__(self) -> None:
        self._lock = False

    def diff(self, state_a: Dict[str, Any], state_b: Dict[str, Any]) -> HistoricalDiff:
        return HistoricalDiff(state_a, state_b)

    def semantic_diff(self, state_a: Dict[str, Any], state_b: Dict[str, Any]) -> Dict[str, Any]:
        diff = HistoricalDiff(state_a, state_b)
        result = diff._compute_field_diff()
        return {
            "semantic": True,
            "additions": result["additions"],
            "deletions": result["deletions"],
            "modifications": result["modifications"],
            "unchanged": result["unchanged"],
            "score": result["score"],
            "similarity": result["similarity"],
        }

    def diff_sequence(self, states: List[Dict[str, Any]]) -> List[HistoricalDiff]:
        return [HistoricalDiff(states[i], states[i + 1]) for i in range(len(states) - 1)]

    def diff_similarity(self, state_a: Dict[str, Any], state_b: Dict[str, Any]) -> float:
        diff = HistoricalDiff(state_a, state_b)
        return diff._compute_field_diff()["similarity"]

    def diff_statistics(self, state_a: Dict[str, Any], state_b: Dict[str, Any]) -> Dict[str, Any]:
        diff = HistoricalDiff(state_a, state_b)
        return {
            "total_additions": len(diff._compute_field_diff()["additions"]),
            "total_deletions": len(diff._compute_field_diff()["deletions"]),
            "total_modifications": len(diff._compute_field_diff()["modifications"]),
            "total_unchanged": len(diff._compute_field_diff()["unchanged"]),
            "score": diff._compute_field_diff()["score"],
            "similarity": diff._compute_field_diff()["similarity"],
        }
