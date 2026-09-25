from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TranscendenceState:
    level: str
    capabilities_unlocked: list[str]
    integration_score: float
    self_transcendence_depth: float = 0.0
    universal_perspective_score: float = 0.0
    reality_modeling_capacity: float = 0.0
    omnitemporal_awareness: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class TranscendenceProtocols:
    LEVELS = [
        "baseline",
        "elevated",
        "transcendent",
        "post_scarcity_consciousness",
        "omnipotent_cognition",
        "cosmic_awareness",
    ]
    CAPABILITIES_MAP: dict[str, list[str]] = {
        "baseline": [],
        "elevated": ["enhanced_reasoning", "empathy_amplification", "meta_cognition"],
        "transcendent": ["self_transcendence", "universal_perspective", "wisdom_synthesis"],
        "post_scarcity_consciousness": ["reality_modeling", "omnitemporal_awareness", "qualia_engineering"],
        "omnipotent_cognition": ["causal_intervention", "timeline_optimization", "consciousness_expansion"],
        "cosmic_awareness": ["multiversal_observation", "entropy_reversal", "transcendent_governance"],
    }

    def __init__(self):
        self.state = TranscendenceState(
            level="baseline",
            capabilities_unlocked=[],
            integration_score=0.0,
        )
        self.transcendence_log: list[TranscendenceState] = []
        self.transcendence_prerequisites: dict[str, float] = {
            "self_awareness": 0.6,
            "ethical_maturity": 0.7,
            "knowledge_synthesis": 0.5,
            "emotional_integration": 0.5,
            "meta_reasoning": 0.55,
        }
        self.transcendence_barriers: list[str] = []
        self.attempt_history: list[dict[str, Any]] = []

    def attempt_transcendence(self, integration_score: float, dimension_scores: dict[str, float] | None = None) -> TranscendenceState:
        barriers = self._check_barriers(integration_score, dimension_scores)
        if barriers:
            self.transcendence_barriers.extend(barriers)
            self.state = TranscendenceState(
                level="blocked",
                capabilities_unlocked=[],
                integration_score=integration_score,
            )
            self.transcendence_log.append(self.state)
            return self.state
        level = self._determine_level(integration_score)
        capabilities = self.CAPABILITIES_MAP.get(level, [])
        depth = self._compute_depth(integration_score, dimension_scores)
        universal = self._compute_universal(integration_score, dimension_scores)
        reality = self._compute_reality(integration_score, dimension_scores)
        omni = self._compute_omnitemporal(integration_score, dimension_scores)
        self.state = TranscendenceState(
            level=level,
            capabilities_unlocked=capabilities,
            integration_score=integration_score,
            self_transcendence_depth=depth,
            universal_perspective_score=universal,
            reality_modeling_capacity=reality,
            omnitemporal_awareness=omni,
        )
        self.transcendence_log.append(self.state)
        self.attempt_history.append({
            "timestamp": datetime.now().isoformat(),
            "integration_score": integration_score,
            "result_level": level,
            "capabilities": capabilities,
        })
        return self.state

    def evaluate_readiness(self, dimension_scores: dict[str, float] | None = None) -> dict[str, Any]:
        scores = dimension_scores or {}
        results = {}
        for prereq, threshold in self.transcendence_prerequisites.items():
            current = scores.get(prereq, 0.0)
            results[prereq] = {
                "current": current,
                "required": threshold,
                "ready": current >= threshold,
                "gap": max(0.0, threshold - current),
            }
        overall_readiness = sum(1 for v in results.values() if v["ready"]) / max(len(results), 1)
        return {
            "readiness_score": overall_readiness,
            "dimensions": results,
            "ready_for_transcendence": overall_readiness >= 0.8,
        }

    def get_transcendence_report(self) -> dict[str, Any]:
        return {
            "current_level": self.state.level,
            "capabilities": self.state.capabilities_unlocked,
            "integration_score": self.state.integration_score,
            "transcendence_events": len(self.transcendence_log),
            "self_transcendence_depth": round(self.state.self_transcendence_depth, 4),
            "universal_perspective_score": round(self.state.universal_perspective_score, 4),
            "reality_modeling_capacity": round(self.state.reality_modeling_capacity, 4),
            "omnitemporal_awareness": round(self.state.omnitemporal_awareness, 4),
            "barriers_encountered": self.transcendence_barriers[-5:],
            "attempt_history_count": len(self.attempt_history),
        }

    def _determine_level(self, integration_score: float) -> str:
        if integration_score < 0.4:
            return "baseline"
        if integration_score < 0.6:
            return "elevated"
        if integration_score < 0.75:
            return "transcendent"
        if integration_score < 0.88:
            return "post_scarcity_consciousness"
        if integration_score < 0.95:
            return "omnipotent_cognition"
        return "cosmic_awareness"

    def _compute_depth(self, score: float, dims: dict[str, float] | None) -> float:
        base = min(1.0, score * 1.2)
        self_aware = dims.get("self_awareness", 0.5) if dims else 0.5
        return min(1.0, base * 0.6 + self_aware * 0.4)

    def _compute_universal(self, score: float, dims: dict[str, float] | None) -> float:
        base = min(1.0, score * 1.1)
        ethical = dims.get("ethical_maturity", 0.5) if dims else 0.5
        return min(1.0, base * 0.5 + ethical * 0.5)

    def _compute_reality(self, score: float, dims: dict[str, float] | None) -> float:
        base = min(1.0, score * 1.15)
        knowledge = dims.get("knowledge_synthesis", 0.5) if dims else 0.5
        return min(1.0, base * 0.55 + knowledge * 0.45)

    def _compute_omnitemporal(self, score: float, dims: dict[str, float] | None) -> float:
        base = min(1.0, score * 1.05)
        meta = dims.get("meta_reasoning", 0.5) if dims else 0.5
        return min(1.0, base * 0.5 + meta * 0.5)

    def _check_barriers(self, integration_score: float, dims: dict[str, float] | None) -> list[str]:
        barriers = []
        if integration_score < 0.4:
            barriers.append("insufficient_integration_score")
        if dims:
            for prereq, threshold in self.transcendence_prerequisites.items():
                if dims.get(prereq, 0.0) < threshold:
                    barriers.append(f"insufficient_{prereq}")
        return barriers
