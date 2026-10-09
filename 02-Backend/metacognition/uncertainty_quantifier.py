import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class UncertaintyEstimate:
    total: float
    aleatoric: float
    epistemic: float
    entropy: float


class UncertaintyQuantifier:
    def __init__(self, epsilon: float = 1e-9):
        self.epsilon = epsilon
        self.class_histories: Dict[str, List[float]] = {}
        self.uncertainty_history: Dict[str, List[float]] = {}

    def record_prediction(self, key: str, confidence: float) -> None:
        if key not in self.uncertainty_history:
            self.uncertainty_history[key] = []
        self.uncertainty_history[key].append(confidence)

    def aleatoric(self, probabilities: List[float]) -> float:
        probs = [max(self.epsilon, min(1.0 - self.epsilon, p)) for p in probabilities]
        entropy = -sum(p * math.log(p) for p in probs if p > self.epsilon)
        return entropy

    def epistemic(self, probabilities: List[float], prior: float = 0.5) -> float:
        avg = sum(probabilities) / len(probabilities) if probabilities else prior
        return max(0.0, 1.0 - avg)

    def entropy(self, probabilities: List[float]) -> float:
        probs = [max(self.epsilon, min(1.0 - self.epsilon, p)) for p in probabilities]
        return -sum(p * math.log(p) for p in probs if p > self.epsilon)

    def quantify(self, key: str, probabilities: List[float]) -> UncertaintyEstimate:
        probs = [max(self.epsilon, min(1.0 - self.epsilon, p)) for p in probabilities]
        aleatoric = self.aleatoric(probs)
        epistemic = self.epistemic(probs)
        entropy = self.entropy(probs)
        total = min(1.0, aleatoric + epistemic)
        self.record_prediction(key, 1.0 - total)
        return UncertaintyEstimate(total=total, aleatoric=aleatoric, epistemic=epistemic, entropy=entropy)

    def variance_estimate(self, key: str, confidence: float) -> float:
        conf = max(self.epsilon, min(1.0 - self.epsilon, confidence))
        return (conf * (1.0 - conf)) / (len(self.uncertainty_history.get(key, [])) + 1)

    def mutual_information(self, distributions: List[List[float]]) -> float:
        entropies = [self.entropy(d) for d in distributions]
        avg_entropy = sum(entropies) / len(entropies) if entropies else 0.0
        return avg_entropy

    def sensitivity_analysis(self, key: str, perturbation: float = 0.1) -> float:
        if key not in self.uncertainty_history or not self.uncertainty_history[key]:
            return 0.0
        recent = self.uncertainty_history[key][-10:]
        base_uncertainty = 1.0 - sum(recent) / len(recent)
        perturbed = [c + perturbation for c in recent]
        perturbed = [max(0.0, min(1.0, c)) for c in perturbed]
        perturbed_uncertainty = 1.0 - sum(perturbed) / len(perturbed)
        return abs(perturbed_uncertainty - base_uncertainty)

    def class_uncertainty(self, key: str) -> Dict[str, float]:
        if key not in self.class_histories:
            return {}
        return {cls: 1.0 - sum(samples) / len(samples) for cls, samples in self.class_histories[key].items()}

    def record_class_sample(self, key: str, class_name: str, confidence: float) -> None:
        if key not in self.class_histories:
            self.class_histories[key] = {}
        if class_name not in self.class_histories[key]:
            self.class_histories[key][class_name] = []
        self.class_histories[key][class_name].append(confidence)
