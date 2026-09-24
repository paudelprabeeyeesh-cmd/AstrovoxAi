
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ToolUseEvaluator:
    def __init__(self):
        self.available_tools: list[str] = []
        self.results: list[dict[str, Any]] = []

    def register_tools(self, tools: list[str]) -> None:
        self.available_tools = tools

    def evaluate_tool_selection(self, predicted_tools: list[str], expected_tools: list[str]) -> dict[str, Any]:
        if not expected_tools:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        pred_set = set(predicted_tools)
        exp_set = set(expected_tools)
        tp = len(pred_set & exp_set)
        fp = len(pred_set - exp_set)
        fn = len(exp_set - pred_set)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        return {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    def evaluate_tool_sequence(self, predicted_sequence: list[str], expected_sequence: list[str]) -> dict[str, Any]:
        if not predicted_sequence or not expected_sequence:
            return {"sequence_accuracy": 0.0}
        min_len = min(len(predicted_sequence), len(expected_sequence))
        correct = sum(1 for i in range(min_len) if predicted_sequence[i] == expected_sequence[i])
        accuracy = correct / max(len(expected_sequence), 1)
        return {
            "sequence_accuracy": round(accuracy, 4),
            "predicted_length": len(predicted_sequence),
            "expected_length": len(expected_sequence),
        }

    def evaluate(self, predicted_tools: list[str], expected_tools: list[str], predicted_sequence: list[str] = None, expected_sequence: list[str] = None) -> dict[str, Any]:
        selection = self.evaluate_tool_selection(predicted_tools, expected_tools)
        sequence = self.evaluate_tool_sequence(predicted_sequence or predicted_tools, expected_sequence or expected_tools)
        overall = (selection["f1"] + sequence["sequence_accuracy"]) / 2.0
        result = {
            "selection": selection,
            "sequence": sequence,
            "overall": round(overall, 4),
            "passed": overall >= 0.6,
        }
        self.results.append(result)
        return result
