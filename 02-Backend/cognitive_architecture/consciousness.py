import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass, field
import time


@dataclass
class ContentElement:
    content: Any
    activation: float
    source_module: str
    timestamp: float = field(default_factory=time.time)
    broadcast: bool = False


class GlobalWorkspace:
    def __init__(self, capacity: int = 16, competition_threshold: float = 0.3):
        self.capacity = capacity
        self.competition_threshold = competition_threshold
        self._workspace: List[ContentElement] = []
        self._broadcast_log: List[Dict[str, Any]] = []

    def compete(self, candidates: List[ContentElement]) -> List[ContentElement]:
        activations = np.array([c.activation for c in candidates])
        if len(activations) == 0:
            return []
        max_act = np.max(activations)
        if max_act == 0:
            winners = candidates
        else:
            normalized = activations / max_act
            winners = [c for c, n in zip(candidates, normalized) if n >= self.competition_threshold]
        if len(winners) > self.capacity:
            winners = sorted(winners, key=lambda c: c.activation, reverse=True)[: self.capacity]
        return winners

    def broadcast(self, elements: List[ContentElement]) -> List[ContentElement]:
        broadcasted = []
        for elem in elements:
            elem.broadcast = True
            self._workspace.append(elem)
            self._broadcast_log.append({
                "content": str(elem.content)[:50],
                "activation": elem.activation,
                "source": elem.source_module,
                "timestamp": elem.timestamp,
            })
            broadcasted.append(elem)
        if len(self._workspace) > self.capacity:
            self._workspace = sorted(self._workspace, key=lambda e: e.activation, reverse=True)[: self.capacity]
        return broadcasted

    def get_current_contents(self) -> List[Dict[str, Any]]:
        return [
            {
                "content": str(e.content)[:50],
                "activation": e.activation,
                "source": e.source_module,
                "broadcast": e.broadcast,
            }
            for e in self._workspace
        ]


class IntegratedInformationCalculator:
    def __init__(self, n_elements: int = 32):
        self.n_elements = n_elements

    def compute_phi(self, elements: np.ndarray, connectivity: np.ndarray) -> float:
        if elements.size == 0 or connectivity.size == 0:
            return 0.0
        if connectivity.shape != (len(elements), len(elements)):
            n = min(len(elements), self.n_elements)
            connectivity = np.eye(n)
        mutual_info = self._mutual_information(elements, connectivity)
        phi = float(np.mean(mutual_info) * np.log(len(elements) + 1))
        return max(0.0, min(1.0, phi))

    def _mutual_information(self, x: np.ndarray, connectivity: np.ndarray) -> np.ndarray:
        n = len(x)
        if n <= 1:
            return np.array([0.0])
        mi = np.zeros(n)
        for i in range(n):
            neighbors = np.where(connectivity[i] > 0)[0]
            if len(neighbors) == 0:
                continue
            x_i = x[i]
            x_neighbors = x[neighbors]
            corr = np.mean(np.abs(x_i - np.mean(x_neighbors)))
            mi[i] = 1.0 / (1.0 + corr) if corr > 0 else 1.0
        return mi

    def partition_info(self, elements: np.ndarray, parts: int = 2) -> Dict[str, float]:
        n = len(elements)
        if n < 2:
            return {"phi_full": 0.0, "phi_partitioned": 0.0, "loss": 0.0}
        size = n // parts
        phi_full = self.compute_phi(elements, np.eye(n))
        phi_partitioned = 0.0
        for i in range(parts):
            start = i * size
            end = n if i == parts - 1 else (i + 1) * size
            part = elements[start:end]
            phi_partitioned += self.compute_phi(part, np.eye(len(part)))
        phi_partitioned /= parts
        return {
            "phi_full": phi_full,
            "phi_partitioned": phi_partitioned,
            "loss": max(0.0, phi_full - phi_partitioned),
        }


class ConsciousnessMonitor:
    def __init__(self, capacity: int = 16):
        self.workspace = GlobalWorkspace(capacity=capacity)
        self.phi_calculator = IntegratedInformationCalculator()
        self._awareness_level: float = 0.0
        self._consciousness_log: List[Dict[str, Any]] = []

    def update(self, inputs: List[ContentElement]) -> Dict[str, Any]:
        winners = self.workspace.compete(inputs)
        broadcasted = self.workspace.broadcast(winners)
        activations = np.array([e.activation for e in broadcasted])
        if len(activations) > 0:
            connectivity = np.eye(len(activations))
            phi = self.phi_calculator.compute_phi(activations, connectivity)
            self._awareness_level = phi * np.mean(activations) if len(activations) > 0 else 0.0
        else:
            phi = 0.0
        state = {
            "awareness_level": float(self._awareness_level),
            "phi": float(phi),
            "broadcast_count": len(broadcasted),
            "contents": self.workspace.get_current_contents(),
        }
        self._consciousness_log.append({**state, "timestamp": time.time()})
        return state

    def get_awareness_level(self) -> float:
        return float(self._awareness_level)

    def get_consciousness_metrics(self) -> Dict[str, Any]:
        if not self._consciousness_log:
            return {"status": "no_data"}
        recent = self._consciousness_log[-10:]
        return {
            "current_awareness": self._awareness_level,
            "avg_awareness": float(np.mean([c["awareness_level"] for c in recent])),
            "total_updates": len(self._consciousness_log),
        }
