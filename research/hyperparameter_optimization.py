import logging
from typing import Dict, List
import random
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class HyperparameterOptimizer:
    def __init__(self, model_factory, search_space: Dict[str, List], steps: int = 10):
        self.model_factory = model_factory
        self.search_space = search_space
        self.steps = steps
        self.results: List[Dict] = []

    def _sample(self) -> Dict:
        return {k: random.choice(v) for k, v in self.search_space.items()}

    def _evaluate(self, params: Dict) -> float:
        model = self.model_factory(**params)
        dummy = torch.randn(2, params.get("seq_len", 32), params.get("hidden_size", 128))
        with torch.no_grad():
            out = model(dummy)
            loss = out.sum().abs().item()
        return loss

    def optimize(self) -> Dict:
        best_params = None
        best_score = float("inf")
        for step in range(self.steps):
            params = self._sample()
            score = self._evaluate(params)
            self.results.append({"step": step + 1, "params": params, "score": score})
            if score < best_score:
                best_score = score
                best_params = params
            logger.info("Step %d: params=%s score=%.4f", step + 1, params, score)
        logger.info("Best params: %s score=%.4f", best_params, best_score)
        return best_params or {}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    def tiny_model(hidden_size=128, num_layers=2, seq_len=32):
        return nn.Sequential(nn.Linear(hidden_size, hidden_size), nn.ReLU(), nn.Linear(hidden_size, 10))

    optimizer = HyperparameterOptimizer(
        model_factory=tiny_model,
        search_space={
            "hidden_size": [64, 128, 256],
            "num_layers": [1, 2, 3],
            "seq_len": [16, 32, 64],
        },
        steps=5,
    )
    optimizer.optimize()
