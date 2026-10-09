from typing import List, Optional


class ConvergenceMonitor:
    def __init__(self, window: int = 10, tol: float = 1e-6) -> None:
        self.window = int(window)
        self.tol = float(tol)
        self.losses: List[float] = []

    def update(self, loss: float) -> None:
        self.losses.append(float(loss))

    def converged(self) -> bool:
        if len(self.losses) < self.window:
            return False
        recent = self.losses[-self.window :]
        return max(recent) - min(recent) < self.tol

    def reset(self) -> None:
        self.losses.clear()
