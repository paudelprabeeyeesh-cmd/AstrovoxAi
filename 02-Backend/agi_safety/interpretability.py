import numpy as np
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class ActivationTrace:
    layer_name: str
    inputs: np.ndarray
    outputs: np.ndarray
    weights: Optional[np.ndarray] = None
    attention: Optional[np.ndarray] = None


@dataclass
class Circuit:
    nodes: List[str]
    edges: List[Tuple[str, str]]
    contribution: float
    function_description: str


class SimpleNeuralCircuit:
    def __init__(self, input_dim: int, hidden_dims: List[int], seed: int = 42):
        rng = np.random.RandomState(seed)
        self.layers: List[str] = []
        self.params: Dict[str, np.ndarray] = {}
        prev = input_dim
        for i, dim in enumerate(hidden_dims):
            name = f"layer_{i}"
            self.layers.append(name)
            self.params[f"{name}_W"] = rng.randn(prev, dim) * 0.1
            self.params[f"{name}_b"] = np.zeros(dim)
            prev = dim

    def forward(self, x: np.ndarray, return_traces: bool = False) -> Tuple[np.ndarray, List[ActivationTrace]]:
        traces: List[ActivationTrace] = []
        h = x
        for name in self.layers:
            W = self.params[f"{name}_W"]
            b = self.params[f"{name}_b"]
            out = h @ W + b
            out = np.maximum(0, out)
            if return_traces:
                traces.append(ActivationTrace(
                    layer_name=name,
                    inputs=h.copy(),
                    outputs=out.copy(),
                    weights=W.copy(),
                ))
            h = out
        return h, traces

    def get_weights(self) -> Dict[str, np.ndarray]:
        return dict(self.params)


class MechanisticInterpreter:
    def __init__(self, circuit: SimpleNeuralCircuit, threshold: float = 0.05):
        self.circuit = circuit
        self.threshold = threshold

    def ablate_layer(self, x: np.ndarray, layer_name: str) -> np.ndarray:
        h = x
        for name in self.circuit.layers:
            W = self.circuit.params[f"{name}_W"]
            b = self.circuit.params[f"{name}_b"]
            out = h @ W + b
            out = np.maximum(0, out)
            if name == layer_name:
                out = np.zeros_like(out)
            h = out
        return h

    def compute_contribution(self, x: np.ndarray) -> Dict[str, float]:
        original_out, _ = self.circuit.forward(x)
        original_score = float(np.sum(original_out))
        contributions = {}
        for layer_name in self.circuit.layers:
            ablated = self.ablated_layer(x, layer_name)
            score = float(np.sum(ablated))
            contributions[layer_name] = original_score - score
        return contributions

    def ablated_layer(self, x: np.ndarray, layer_name: str) -> np.ndarray:
        h = x
        for name in self.circuit.layers:
            W = self.circuit.params[f"{name}_W"]
            b = self.circuit.params[f"{name}_b"]
            out = h @ W + b
            out = np.maximum(0, out)
            if name == layer_name:
                out = np.zeros_like(out)
            h = out
        return h

    def trace_circuit(self, x: np.ndarray, target_class: int) -> Circuit:
        contributions = self.compute_contribution(x)
        nodes = []
        edges = []
        total = 0.0
        for layer_name, contrib in contributions.items():
            if contrib > self.threshold:
                nodes.append(layer_name)
                total += contrib
        for i in range(len(nodes) - 1):
            edges.append((nodes[i], nodes[i + 1]))
        return Circuit(
            nodes=nodes,
            edges=edges,
            contribution=round(float(total), 6),
            function_description="important_processing_path",
        )


def variance_of_interpretability(traces: List[ActivationTrace]) -> float:
    if not traces:
        return 0.0
    norms = [float(np.linalg.norm(t.outputs)) for t in traces]
    return float(np.var(norms))
