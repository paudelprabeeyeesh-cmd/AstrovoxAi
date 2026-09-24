from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np


@dataclass
class ConfidenceState:
    overall: float = 0.0
    dimensions: Dict[str, float] = field(default_factory=dict)
    uncertainty: float = 0.0
    calibration_error: float = 0.0


class MetacognitiveMonitor:
    def __init__(self, decay_rate: float = 0.95):
        self.decay_rate = decay_rate
        self.history: List[ConfidenceState] = []
        self.task_difficulty: Dict[str, float] = {}

    def track(self, task_id: str, performance: float, expected_difficulty: float) -> ConfidenceState:
        actual_difficulty = expected_difficulty
        if task_id in self.task_difficulty:
            actual_difficulty = self.task_difficulty[task_id] * self.decay_rate + expected_difficulty * (1 - self.decay_rate)
        self.task_difficulty[task_id] = actual_difficulty
        confidence = performance / max(actual_difficulty, 1e-6)
        confidence = max(0.0, min(1.0, confidence))
        uncertainty = 1.0 - confidence
        calibration = self._calibration(confidence, performance)
        state = ConfidenceState(overall=confidence, uncertainty=uncertainty, calibration_error=calibration)
        self.history.append(state)
        return state

    def estimate_uncertainty(self, task_id: str, evidence_count: int, coherence: float) -> float:
        if task_id not in self.task_difficulty:
            self.task_difficulty[task_id] = 0.5
        difficulty = self.task_difficulty[task_id]
        evidence_factor = np.exp(-evidence_count * 0.2)
        uncertainty = difficulty * evidence_factor * (1.0 - coherence)
        return max(0.0, min(1.0, uncertainty))

    def know_what_you_know(self, task_id: str, performance: float, evidence_count: int) -> Dict[str, float]:
        confidence = performance * np.log1p(evidence_count) / (1.0 + self.task_difficulty.get(task_id, 0.5))
        confidence = max(0.0, min(1.0, confidence))
        return {"confidence": confidence, "uncertainty": 1.0 - confidence, "knows_boundary": confidence > 0.7}

    def detect_unknowns(self, task_id: str, performance: float, coherence: float) -> List[str]:
        unknowns = []
        uncertainty = self.estimate_uncertainty(task_id, 0, coherence)
        if uncertainty > 0.6:
            unknowns.append("High uncertainty detected")
        if coherence < 0.5:
            unknowns.append("Low coherence in reasoning")
        if performance < 0.4:
            unknowns.append("Poor performance on task")
        return unknowns

    def _calibration(self, confidence: float, performance: float) -> float:
        return abs(confidence - performance)

    def get_calibration_report(self) -> Dict[str, float]:
        if not self.history:
            return {"mean_calibration_error": 0.0, "overconfidence_rate": 0.0}
        errors = [h.calibration_error for h in self.history]
        overconfident = sum(1 for h in self.history if h.overall > 0.7 and h.calibration_error > 0.2)
        return {
            "mean_calibration_error": float(np.mean(errors)),
            "overconfidence_rate": overconfident / len(self.history),
        }

    def update_belief(self, belief_key: str, evidence: float, prior: Optional[float] = None) -> float:
        if prior is None:
            prior = self.task_difficulty.get(belief_key, 0.5)
        updated = prior * 0.7 + evidence * 0.3
        self.task_difficulty[belief_key] = updated
        return updated
