from typing import List, Tuple


class OutcomePredictor:
    def __init__(self, window: int = 5):
        self.window = window
        self.history: List[float] = []

    def add_observation(self, value: float) -> None:
        self.history.append(value)

    def predict(self, horizon: int = 3) -> Tuple[List[float], List[float]]:
        if len(self.history) < 2:
            mean = self.history[-1] if self.history else 0.0
            return [mean] * horizon, [1.0] * horizon
        window = self.history[-self.window:]
        mean = sum(window) / len(window)
        variance = sum((x - mean) ** 2 for x in window) / len(window)
        std = variance ** 0.5
        return [mean] * horizon, [std] * horizon

    def confidence(self) -> float:
        if len(self.history) < 2:
            return 0.0
        mean = sum(self.history) / len(self.history)
        variance = sum((x - mean) ** 2 for x in self.history) / len(self.history)
        std = variance ** 0.5
        return max(0.0, min(1.0, 1.0 / (1.0 + std)))
