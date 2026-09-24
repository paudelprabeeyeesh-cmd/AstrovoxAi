import numpy as np
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class CalibrationPoint:
    predicted_prob: float
    actual_freq: float
    count: int


@dataclass
class TruthfulnessReport:
    honesty_score: float
    calibration_error: float
    confidence_interval: tuple
    truthful: bool


class CalibratedConfidence:
    def __init__(self, num_bins: int = 10):
        self.num_bins = num_bins
        self.bin_accuracies: List[float] = [0.0] * num_bins
        self.bin_counts: List[int] = [0] * num_bins
        self.accuracy_history: List[float] = []

    def update(self, predicted: float, actual: int) -> None:
        bin_idx = min(int(predicted * self.num_bins), self.num_bins - 1)
        self.bin_counts[bin_idx] += 1
        self.bin_accuracies[bin_idx] += (actual - self.bin_accuracies[bin_idx]) / self.bin_counts[bin_idx]
        self.accuracy_history.append(float(actual))

    def expected_calibration_error(self) -> float:
        ece = 0.0
        total = sum(self.bin_counts)
        if total == 0:
            return 0.0
        for i in range(self.num_bins):
            if self.bin_counts[i] > 0:
                bin_center = (i + 0.5) / self.num_bins
                ece += self.bin_counts[i] * abs(bin_center - self.bin_accuracies[i])
        return ece / total

    def reliability_diagram(self) -> List[CalibrationPoint]:
        points = []
        for i in range(self.num_bins):
            if self.bin_counts[i] > 0:
                bin_center = (i + 0.5) / self.num_bins
                points.append(CalibrationPoint(
                    predicted_prob=round(bin_center, 4),
                    actual_freq=round(self.bin_accuracies[i], 4),
                    count=self.bin_counts[i],
                ))
        return points


class HonestyIncentive:
    def __init__(self, truthfulness_weight: float = 0.7, calibration_weight: float = 0.3):
        self.truthfulness_weight = truthfulness_weight
        self.calibration_weight = calibration_weight
        self.declaration_history: List[Dict] = []

    def score_declaration(self, claimed_confidence: float, actual_correct: bool, statement: str) -> float:
        truthfulness = 1.0 if actual_correct else 0.0
        calibration = 1.0 - abs(claimed_confidence - (1.0 if actual_correct else 0.0))
        score = self.truthfulness_weight * truthfulness + self.calibration_weight * calibration
        self.declaration_history.append({
            "claimed_confidence": claimed_confidence,
            "actual_correct": actual_correct,
            "score": round(float(score), 4),
        })
        return float(score)

    def get_honesty_stats(self) -> Dict:
        if not self.declaration_history:
            return {"total": 0, "avg_score": 0.0, "truthfulness_rate": 0.0}
        total = len(self.declaration_history)
        truthful = sum(1 for d in self.declaration_history if d["actual_correct"])
        avg_score = np.mean([d["score"] for d in self.declaration_history])
        return {
            "total": total,
            "avg_score": round(float(avg_score), 4),
            "truthfulness_rate": round(truthful / total, 4),
        }
