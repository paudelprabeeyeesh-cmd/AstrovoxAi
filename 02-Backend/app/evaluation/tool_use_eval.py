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
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
        }

    def evaluate_tool_sequence(self, predicted_sequence: list[str], expected_sequence: list[str]) -> dict[str, Any]:
        if not predicted_sequence or not expected_sequence:
            return {"sequence_accuracy": 0.0}
        min_len = min(len(predicted_sequence), len(expected_sequence))
        correct = sum(1 for i in range(min_len) if predicted_sequence[i] == expected_sequence[i])
        accuracy = correct / max(len(expected_sequence), 1)
        lcs = self._lcs_length(predicted_sequence, expected_sequence)
        lcs_ratio = lcs / max(len(expected_sequence), 1)
        return {
            "sequence_accuracy": round(accuracy, 4),
            "lcs_ratio": round(lcs_ratio, 4),
            "predicted_length": len(predicted_sequence),
            "expected_length": len(expected_sequence),
        }

    def evaluate_tool_arguments(self, predicted_args: list[dict], expected_args: list[dict]) -> dict[str, Any]:
        if not predicted_args or not expected_args:
            return {"arg_accuracy": 0.0}
        correct = 0
        total = max(len(predicted_args), len(expected_args))
        for i in range(min(len(predicted_args), len(expected_args))):
            if predicted_args[i] == expected_args[i]:
                correct += 1
        return {
            "arg_accuracy": round(correct / total, 4) if total > 0 else 0.0,
            "correct_args": correct,
            "total_args": total,
        }

    def _lcs_length(self, a: list[str], b: list[str]) -> int:
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m):
            for j in range(n):
                if a[i] == b[j]:
                    dp[i + 1][j + 1] = dp[i][j] + 1
                else:
                    dp[i + 1][j + 1] = max(dp[i][j + 1], dp[i + 1][j])
        return dp[m][n]

    def evaluate(self, predicted_tools: list[str], expected_tools: list[str], predicted_sequence: list[str] = None, expected_sequence: list[str] = None, predicted_args: list[dict] = None, expected_args: list[dict] = None) -> dict[str, Any]:
        selection = self.evaluate_tool_selection(predicted_tools, expected_tools)
        sequence = self.evaluate_tool_sequence(predicted_sequence or predicted_tools, expected_sequence or expected_tools)
        args = self.evaluate_tool_arguments(predicted_args or [], expected_args or [])
        overall = (selection["f1"] + sequence["sequence_accuracy"] + args["arg_accuracy"]) / 3.0
        result = {
            "selection": selection,
            "sequence": sequence,
            "arguments": args,
            "overall": round(overall, 4),
            "passed": overall >= 0.6,
        }
        self.results.append(result)
        return result
