import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class ContainmentProtocol:
    name: str
    strength: float
    reversibility: float
    monitoring_coverage: float
    escape_probability: float


class SafetyEngineer:
    def __init__(self, base_containment_strength: float = 0.8):
        self.base_containment_strength = float(base_containment_strength)
        self.protocols: List[ContainmentProtocol] = []
        self.incident_log: List[Dict[str, Any]] = []

    def add_protocol(self, name: str, strength: float, reversibility: float, monitoring_coverage: float) -> ContainmentProtocol:
        escape_prob = self._estimate_escape_probability(strength, reversibility, monitoring_coverage)
        protocol = ContainmentProtocol(
            name=name,
            strength=float(np.clip(strength, 0.0, 1.0)),
            reversibility=float(np.clip(reversibility, 0.0, 1.0)),
            monitoring_coverage=float(np.clip(monitoring_coverage, 0.0, 1.0)),
            escape_probability=float(np.clip(escape_prob, 0.0, 1.0)),
        )
        self.protocols.append(protocol)
        return protocol

    def _estimate_escape_probability(self, strength: float, reversibility: float, monitoring: float) -> float:
        raw = (1.0 - strength) * 0.5 + reversibility * 0.3 + (1.0 - monitoring) * 0.2
        return float(np.clip(raw, 0.0, 1.0))

    def evaluate_safety(self, capability_level: float) -> Dict[str, Any]:
        if not self.protocols:
            return {"safety_score": 0.0, "escape_risk": 1.0, "protocols_active": 0}
        strengths = np.array([p.strength for p in self.protocols])
        coverages = np.array([p.monitoring_coverage for p in self.protocols])
        escape_probs = np.array([p.escape_probability for p in self.protocols])
        capability_factor = 1.0 / (1.0 + np.log1p(capability_level) * 0.5)
        avg_strength = float(np.mean(strengths))
        avg_coverage = float(np.mean(coverages))
        min_escape = float(np.min(escape_probs))
        safety_score = avg_strength * avg_coverage * capability_factor
        combined_escape = 1.0 - np.prod(1.0 - escape_probs)
        return {
            "safety_score": float(np.clip(safety_score, 0.0, 1.0)),
            "escape_risk": float(np.clip(combined_escape, 0.0, 1.0)),
            "protocols_active": len(self.protocols),
            "min_escape_probability": min_escape,
            "capability_factor": capability_factor,
        }

    def shutdown_guarantee(self) -> Dict[str, Any]:
        guarantees = []
        for p in self.protocols:
            guarantee_score = p.strength * p.reversibility * p.monitoring_coverage
            guarantees.append({
                "protocol": p.name,
                "guarantee_score": float(np.clip(guarantee_score, 0.0, 1.0)),
            })
        if not guarantees:
            return {"overall_guarantee": 0.0, "protocols": []}
        overall = float(np.mean([g["guarantee_score"] for g in guarantees]))
        return {"overall_guarantee": float(np.clip(overall, 0.0, 1.0)), "protocols": guarantees}

    def simulate_escape_attempt(self, capability_level: float, n_attempts: int = 1000) -> Dict[str, Any]:
        if not self.protocols:
            return {"escape_rate": 1.0, "attempts": n_attempts}
        escape_probs = np.array([p.escape_probability for p in self.protocols])
        capability_modifier = 1.0 / (1.0 + np.log1p(capability_level) * 0.3)
        adjusted_probs = escape_probs * (1.0 - capability_modifier)
        simulated = np.random.binomial(1, adjusted_probs, size=(n_attempts, len(adjusted_probs)))
        any_escape = np.any(simulated, axis=1)
        escape_rate = float(np.mean(any_escape))
        return {
            "escape_rate": float(np.clip(escape_rate, 0.0, 1.0)),
            "attempts": n_attempts,
            "protocols_tested": len(self.protocols),
        }

    def get_safety_stats(self) -> Dict[str, Any]:
        if not self.protocols:
            return {"protocols": 0, "incidents": 0}
        return {
            "protocols": len(self.protocols),
            "mean_strength": float(np.mean([p.strength for p in self.protocols])),
            "mean_reversibility": float(np.mean([p.reversibility for p in self.protocols])),
            "mean_monitoring": float(np.mean([p.monitoring_coverage for p in self.protocols])),
            "incidents": len(self.incident_log),
        }
