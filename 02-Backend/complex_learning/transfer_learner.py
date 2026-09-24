from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class KnowledgeModule:
    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    frozen: bool = False
    source_domain: str = "source"


class TransferLearner:
    def __init__(self, input_dim: int, output_dim: int):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.modules: Dict[str, KnowledgeModule] = {}
        self.target_accuracy: Optional[float] = None
        self.source_accuracy: Optional[float] = None
        self.transfer_log: List[Dict] = []

    def add_module(self, name: str, params: Optional[Dict[str, Any]] = None, source_domain: str = "source") -> None:
        self.modules[name] = KnowledgeModule(name=name, params=params or {}, source_domain=source_domain)

    def freeze_module(self, name: str) -> None:
        if name not in self.modules:
            raise KeyError(f"Module '{name}' not found")
        self.modules[name].frozen = True

    def unfreeze_module(self, name: str) -> None:
        if name not in self.modules:
            raise KeyError(f"Module '{name}' not found")
        self.modules[name].frozen = False

    def load_source_weights(self, module_name: str, weights: Dict[str, Any]) -> None:
        if module_name not in self.modules:
            raise KeyError(f"Module '{module_name}' not found")
        self.modules[module_name].params.update(weights)

    def _compute_loss(self, predictions: List[float], targets: List[int]) -> float:
        correct = sum(1 for p, t in zip(predictions, targets) if p == t)
        return 1.0 - (correct / len(targets)) if targets else 0.0

    def adapt_to_target(self, x: List[List[float]], y: List[int], lr: float = 0.01, epochs: int = 1) -> float:
        if len(x) != len(y) or not x:
            raise ValueError("x and y must be non-empty and aligned")
        if not self.modules:
            raise RuntimeError("No modules registered")
        for _ in range(epochs):
            predictions = [0] * len(y)
            for name, module in self.modules.items():
                if module.frozen:
                    continue
                for i, sample in enumerate(x):
                    raw = sum(sample) / len(sample) if sample else 0.0
                    predictions[i] = 1 if raw > 0.5 else 0
            loss = self._compute_loss(predictions, y)
            self.target_accuracy = 1.0 - loss
        self.transfer_log.append({"action": "adapt", "loss": loss, "epochs": epochs})
        return loss

    def evaluate_source(self, x: List[List[float]], y: List[int]) -> float:
        if len(x) != len(y) or not x:
            raise ValueError("x and y must be non-empty and aligned")
        predictions = []
        for sample in x:
            raw = sum(sample) / len(sample) if sample else 0.0
            predictions.append(1 if raw > 0.5 else 0)
        loss = self._compute_loss(predictions, y)
        self.source_accuracy = 1.0 - loss
        self.transfer_log.append({"action": "evaluate_source", "accuracy": self.source_accuracy})
        return loss

    def summary(self) -> Dict[str, Any]:
        return {
            "modules": list(self.modules.keys()),
            "frozen": [n for n, m in self.modules.items() if m.frozen],
            "source_accuracy": self.source_accuracy,
            "target_accuracy": self.target_accuracy,
        }
