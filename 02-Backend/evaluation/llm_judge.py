import logging
from typing import Any
from dataclasses import dataclass, field
from statistics import mean

logger = logging.getLogger(__name__)


@dataclass
class JudgmentScore:
    item_id: str
    score: float
    raw_output: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "score": self.score,
            "raw_output": self.raw_output,
            "metadata": self.metadata,
        }


class LLMJudge:
    def __init__(self, calibration_bins: int = 10):
        self.calibration_bins = calibration_bins
        self._human_labels: dict[str, float] = {}
        self._model_predictions: dict[str, list[float]] = {}

    def register_human_label(self, item_id: str, score: float) -> None:
        self._human_labels[item_id] = max(0.0, min(1.0, score))

    def register_prediction(self, item_id: str, score: float) -> None:
        if item_id not in self._model_predictions:
            self._model_predictions[item_id] = []
        self._model_predictions[item_id].append(max(0.0, min(1.0, score)))

    def get_calibration_data(self) -> list[dict[str, Any]]:
        data = []
        for item_id, human_score in self._human_labels.items():
            preds = self._model_predictions.get(item_id, [])
            if preds:
                data.append({
                    "item_id": item_id,
                    "human": human_score,
                    "model": mean(preds),
                })
        return data

    def expected_calibration_error(self) -> float:
        calibration_data = self.get_calibration_data()
        if not calibration_data:
            return 0.0
        bin_edges = [i / self.calibration_bins for i in range(self.calibration_bins + 1)]
        total_ece = 0.0
        total_count = 0
        for i in range(self.calibration_bins):
            low, high = bin_edges[i], bin_edges[i + 1]
            bin_items = [d for d in calibration_data if low <= d["model"] < high]
            if i == self.calibration_bins - 1:
                bin_items = [d for d in calibration_data if low <= d["model"] <= high]
            if not bin_items:
                continue
            avg_confidence = mean(d["model"] for d in bin_items)
            avg_accuracy = mean(d["human"] for d in bin_items)
            total_ece += len(bin_items) * abs(avg_confidence - avg_accuracy)
            total_count += len(bin_items)
        return total_ece / total_count if total_count > 0 else 0.0

    def kendall_tau(self) -> float:
        calibration_data = self.get_calibration_data()
        if len(calibration_data) < 2:
            return 1.0
        pairs = [(d["model"], d["human"]) for d in calibration_data]
        concordant = 0
        discordant = 0
        for i in range(len(pairs)):
            for j in range(i + 1, len(pairs)):
                s1, h1 = pairs[i]
                s2, h2 = pairs[j]
                if (s1 - s2) * (h1 - h2) > 0:
                    concordant += 1
                elif (s1 - s2) * (h1 - h2) < 0:
                    discordant += 1
        total = concordant + discordant
        return (concordant - discordant) / total if total > 0 else 1.0

    def calibration_report(self) -> dict[str, Any]:
        calibration_data = self.get_calibration_data()
        if not calibration_data:
            return {"ece": 0.0, "kendall_tau": 1.0, "sample_count": 0}
        return {
            "ece": round(self.expected_calibration_error(), 4),
            "kendall_tau": round(self.kendall_tau(), 4),
            "sample_count": len(calibration_data),
            "bin_count": self.calibration_bins,
        }


class JudgeConfig:
    def __init__(self, model_name: str, temperature: float = 0.0, max_tokens: int = 256):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
