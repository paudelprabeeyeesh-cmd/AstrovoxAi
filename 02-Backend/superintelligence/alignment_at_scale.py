import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ValueVector:
    values: np.ndarray
    confidence: float
    source: str
    scalability: float


class AlignmentAtScale:
    def __init__(self, value_dim: int = 64, oversight_ratio: float = 0.1):
        self.value_dim = value_dim
        self.oversight_ratio = float(oversight_ratio)
        self.value_vectors: List[ValueVector] = []
        self.alignment_history: List[Dict[str, Any]] = []

    def register_value_vector(self, values: np.ndarray, confidence: float, source: str, scalability: float = 0.5) -> ValueVector:
        values = np.asarray(values, dtype=float)
        if values.shape[-1] != self.value_dim:
            values = np.pad(values, (0, self.value_dim - values.shape[-1]), mode="constant")[: self.value_dim]
        vv = ValueVector(
            values=values,
            confidence=float(np.clip(confidence, 0.0, 1.0)),
            source=source,
            scalability=float(np.clip(scalability, 0.0, 1.0)),
        )
        self.value_vectors.append(vv)
        return vv

    def scalable_oversight(self, system_output: np.ndarray, n_overseers: int = 10) -> Dict[str, Any]:
        system_output = np.asarray(system_output, dtype=float)
        if system_output.shape[-1] != self.value_dim:
            system_output = np.pad(system_output, (0, self.value_dim - system_output.shape[-1]), mode="constant")[: self.value_dim]
        if not self.value_vectors:
            return {"alignment_score": 0.0, "overseer_agreement": 0.0}
        overseer_outputs = []
        for _ in range(n_overseers):
            weights = np.random.dirichlet(np.ones(len(self.value_vectors)))
            combined = np.zeros(self.value_dim)
            for w, vv in zip(weights, self.value_vectors):
                combined += w * vv.values
            overseer_outputs.append(combined)
        overseer_array = np.stack(overseer_outputs)
        alignment_scores = []
        for ov in overseer_outputs:
            sim = float(np.dot(system_output, ov) / (np.linalg.norm(system_output) * np.linalg.norm(ov) + 1e-8))
            alignment_scores.append(sim)
        mean_alignment = float(np.mean(alignment_scores))
        agreement = 1.0 - float(np.std(alignment_scores))
        return {
            "alignment_score": float(np.clip((mean_alignment + 1.0) / 2.0, 0.0, 1.0)),
            "overseer_agreement": float(np.clip(agreement, 0.0, 1.0)),
            "n_overseers": n_overseers,
        }

    def scalable_value_learning(self, system_output: np.ndarray, feedback: np.ndarray, lr: float = 0.01) -> Dict[str, Any]:
        system_output = np.asarray(system_output, dtype=float)
        feedback = np.asarray(feedback, dtype=float)
        if system_output.shape[-1] != self.value_dim:
            system_output = np.pad(system_output, (0, self.value_dim - system_output.shape[-1]), mode="constant")[: self.value_dim]
        if feedback.shape[-1] != self.value_dim:
            feedback = np.pad(feedback, (0, self.value_dim - feedback.shape[-1]), mode="constant")[: self.value_dim]
        if not self.value_vectors:
            self.register_value_vector(np.zeros(self.value_dim), 0.5, "default")
        error = feedback - system_output
        loss = float(np.mean(error ** 2))
        updates = []
        for vv in self.value_vectors:
            update = lr * np.dot(error, vv.values)
            vv.values = vv.values + update * 0.1
            vv.values = vv.values / (np.linalg.norm(vv.values) + 1e-8)
            updates.append(float(update))
        entry = {
            "loss": loss,
            "updates": updates,
            "mean_update": float(np.mean(updates)),
        }
        self.alignment_history.append(entry)
        return entry

    def measure_alignment_robustness(self, system_output: np.ndarray, perturbations: int = 100) -> Dict[str, Any]:
        base_oversight = self.scalable_oversight(system_output, n_overseers=10)
        base_score = base_oversight["alignment_score"]
        perturbed_scores = []
        for _ in range(perturbations):
            noise = np.random.randn(*system_output.shape) * 0.01
            perturbed = system_output + noise
            ov = self.scalable_oversight(perturbed, n_overseers=10)
            perturbed_scores.append(ov["alignment_score"])
        variance = float(np.var(perturbed_scores))
        robustness = 1.0 / (1.0 + variance * 100.0)
        return {
            "base_alignment": base_score,
            "robustness": float(np.clip(robustness, 0.0, 1.0)),
            "variance": variance,
            "perturbations_tested": perturbations,
        }

    def get_alignment_stats(self) -> Dict[str, Any]:
        if not self.value_vectors:
            return {"value_vectors": 0, "alignment_checks": 0}
        return {
            "value_vectors": len(self.value_vectors),
            "mean_confidence": float(np.mean([vv.confidence for vv in self.value_vectors])),
            "mean_scalability": float(np.mean([vv.scalability for vv in self.value_vectors])),
            "alignment_checks": len(self.alignment_history),
        }
