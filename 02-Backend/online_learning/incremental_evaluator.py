import math
from typing import List, Tuple, Dict, Any


class IncrementalEvaluator:
    def __init__(self):
        self.predictions: List[float] = []
        self.targets: List[float] = []
        self.total_error = 0.0
        self.total_absolute_error = 0.0
        self.total_squared_error = 0.0
        self.step_count = 0

    def update(self, pred: float, target: float) -> Dict[str, Any]:
        error = pred - target
        self.predictions.append(pred)
        self.targets.append(target)
        self.total_error += error
        self.total_absolute_error += abs(error)
        self.total_squared_error += error ** 2
        self.step_count += 1
        return self.get_metrics()

    @staticmethod
    def _mean(values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def _std(values: List[float]) -> float:
        if not values:
            return 0.0
        m = sum(values) / len(values)
        variance = sum((v - m) ** 2 for v in values) / len(values)
        return math.sqrt(variance)

    def get_metrics(self) -> Dict[str, Any]:
        n = self.step_count
        if n == 0:
            return {
                "mae": 0.0,
                "mse": 0.0,
                "rmse": 0.0,
                "bias": 0.0,
                "std_error": 0.0,
                "step_count": 0,
            }
        mae = self.total_absolute_error / n
        mse = self.total_squared_error / n
        rmse = math.sqrt(mse)
        bias = self.total_error / n
        std_error = self._std([p - t for p, t in zip(self.predictions, self.targets)])
        return {
            "mae": mae,
            "mse": mse,
            "rmse": rmse,
            "bias": bias,
            "std_error": std_error,
            "step_count": n,
        }

    def reset(self) -> None:
        self.predictions = []
        self.targets = []
        self.total_error = 0.0
        self.total_absolute_error = 0.0
        self.total_squared_error = 0.0
        self.step_count = 0
