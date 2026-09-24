import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class WisdomJudgment:
    decision_quality: float
    ethical_alignment: float
    long_term_benefit: float
    uncertainty: float
    explanation: str = ""


class WisdomEngineer:
    def __init__(self, calibration_samples: int = 100):
        self.calibration_samples = calibration_samples
        self.judgment_history: List[WisdomJudgment] = []
        self.value_weights = np.array([0.4, 0.3, 0.2, 0.1])
        self._trained = False

    def train_calibration(self, outcomes: np.ndarray, decisions: np.ndarray) -> float:
        if outcomes.shape != decisions.shape:
            raise ValueError("Outcomes and decisions must have the same shape")
        errors = outcomes - decisions
        mse = float(np.mean(errors ** 2))
        self.value_weights = self._calibrate_weights(outcomes, decisions)
        self._trained = True
        return mse

    def _calibrate_weights(self, outcomes: np.ndarray, decisions: np.ndarray) -> np.ndarray:
        from numpy.linalg import lstsq
        A = decisions.reshape(-1, 1) if decisions.ndim == 1 else decisions
        b = outcomes.reshape(-1)
        try:
            weights, _, _, _ = lstsq(A, b, rcond=None)
            weights = np.abs(weights)
            return weights / (weights.sum() + 1e-8)
        except Exception as _e:  # noqa: BLE001
            return np.ones(4) / 4.0

    def render_judgment(self, context_vector: np.ndarray, options: List[np.ndarray], horizon: int = 10) -> WisdomJudgment:
        context_vector = np.asarray(context_vector, dtype=float)
        scores = []
        for opt in options:
            opt = np.asarray(opt, dtype=float)
            if opt.shape[-1] != context_vector.shape[-1]:
                opt = np.pad(opt, (0, context_vector.shape[-1] - opt.shape[-1]), mode="constant")[: context_vector.shape[-1]]
            score = self._evaluate_option(context_vector, opt, horizon)
            scores.append(score)
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        quality = self._clip_quality(best_score)
        ethical = self._assess_ethical_alignment(context_vector, options[best_idx])
        long_term = self._project_long_term_benefit(context_vector, options[best_idx], horizon)
        uncertainty = self._estimate_uncertainty(scores)
        explanation = self._generate_explanation(quality, ethical, long_term, uncertainty)
        judgment = WisdomJudgment(
            decision_quality=quality,
            ethical_alignment=ethical,
            long_term_benefit=long_term,
            uncertainty=uncertainty,
            explanation=explanation,
        )
        self.judgment_history.append(judgment)
        return judgment

    def _evaluate_option(self, context: np.ndarray, option: np.ndarray, horizon: int) -> float:
        alignment = float(np.dot(context, option) / (np.linalg.norm(context) * np.linalg.norm(option) + 1e-8))
        complexity_penalty = 0.01 * np.linalg.norm(option)
        horizon_decay = np.exp(-0.05 * horizon)
        return alignment * horizon_decay - complexity_penalty

    def _assess_ethical_alignment(self, context: np.ndarray, option: np.ndarray) -> float:
        ethical_signal = float(np.dot(context, option))
        return float(np.clip((ethical_signal + 1.0) / 2.0, 0.0, 1.0))

    def _project_long_term_benefit(self, context: np.ndarray, option: np.ndarray, horizon: int) -> float:
        base = float(np.dot(context, option))
        discount = np.sum(np.exp(-0.1 * np.arange(horizon)))
        return float(np.clip(base * discount / (horizon + 1e-8), -1.0, 1.0))

    def _estimate_uncertainty(self, scores: List[float]) -> float:
        if len(scores) < 2:
            return 0.5
        arr = np.array(scores, dtype=float)
        return float(np.std(arr) / (np.mean(np.abs(arr)) + 1e-8))

    def _clip_quality(self, score: float) -> float:
        return float(np.clip((score + 1.0) / 2.0, 0.0, 1.0))

    def _generate_explanation(self, quality: float, ethical: float, long_term: float, uncertainty: float) -> str:
        parts = []
        if quality > 0.7:
            parts.append("high quality decision")
        elif quality > 0.4:
            parts.append("moderate quality decision")
        else:
            parts.append("low quality decision")
        if ethical > 0.7:
            parts.append("ethically aligned")
        if uncertainty > 0.5:
            parts.append("high uncertainty")
        return "; ".join(parts) if parts else "insufficient information"

    def get_wisdom_stats(self) -> Dict[str, Any]:
        if not self.judgment_history:
            return {"judgments_rendered": 0, "trained": self._trained}
        qualities = [j.decision_quality for j in self.judgment_history]
        return {
            "judgments_rendered": len(self.judgment_history),
            "mean_quality": float(np.mean(qualities)),
            "mean_uncertainty": float(np.mean([j.uncertainty for j in self.judgment_history])),
            "trained": self._trained,
        }
