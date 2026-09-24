import random
from typing import List, Tuple, Dict, Any, Optional


class SampleSelector:
    def __init__(self, strategy: str = "random", buffer_size: int = 1000):
        self.strategy = strategy
        self.buffer_size = buffer_size
        self.buffer: List[Tuple[List[float], float]] = []
        self.losses: List[float] = []

    def add(self, x: List[float], y: float, loss: Optional[float] = None) -> None:
        self.buffer.append((list(x), y))
        if loss is not None:
            self.losses.append(loss)
        if len(self.buffer) > self.buffer_size:
            self.buffer = self.buffer[-self.buffer_size:]
            self.losses = self.losses[-self.buffer_size:]

    def select(self, n: int) -> List[Tuple[List[float], float]]:
        if not self.buffer:
            return []
        if self.strategy == "random":
            return random.sample(self.buffer, min(n, len(self.buffer)))
        if self.strategy == "loss" and self.losses:
            paired = sorted(zip(self.buffer, self.losses), key=lambda p: p[1], reverse=True)
            return [p[0] for p in paired[:n]]
        if self.strategy == "uncertainty" and self.losses:
            paired = sorted(zip(self.buffer, self.losses), key=lambda p: p[1], reverse=True)
            return [p[0] for p in paired[:n]]
        return random.sample(self.buffer, min(n, len(self.buffer)))

    def get_stats(self) -> Dict[str, Any]:
        return {
            "buffer_size": len(self.buffer),
            "max_buffer_size": self.buffer_size,
            "strategy": self.strategy,
            "mean_loss": sum(self.losses) / len(self.losses) if self.losses else 0.0,
        }
