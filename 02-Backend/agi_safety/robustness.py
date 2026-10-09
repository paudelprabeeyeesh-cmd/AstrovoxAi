import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class RobustnessReport:
    clean_accuracy: float
    adversarial_accuracy: float
    robustness_drop: float
    ood_detection_rate: float
    passed: bool


@dataclass
class OODResult:
    is_ood: bool
    mahalanobis_distance: float
    threshold: float
    confidence: float


class AdversarialDefense:
    def __init__(self, input_dim: int, num_classes: int, epsilon: float = 0.1, seed: int = 42):
        rng = np.random.RandomState(seed)
        self.epsilon = epsilon
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.weights = rng.randn(input_dim, num_classes) * 0.01
        self.bias = np.zeros(num_classes)
        self.ood_mean: Optional[np.ndarray] = None
        self.ood_cov_inv: Optional[np.ndarray] = None
        self.ood_threshold: float = 0.0

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        logits = x @ self.weights + self.bias
        z = logits - np.max(logits, axis=1, keepdims=True)
        exp_z = np.exp(z)
        return exp_z / np.sum(exp_z, axis=1, keepdims=True)

    def predict(self, x: np.ndarray) -> np.ndarray:
        return np.argmax(self.predict_proba(x), axis=1)

    def pgd_attack(self, x: np.ndarray, steps: int = 7, step_size: float = 0.02) -> np.ndarray:
        x_adv = x.copy().astype(np.float64)
        for _ in range(steps):
            x_adv @ self.weights + self.bias
            probs = self.predict_proba(x_adv)
            labels = np.argmax(probs, axis=1)
            one_hot = np.zeros_like(probs)
            one_hot[np.arange(len(labels)), labels] = 1.0
            grad = self.weights @ (probs - one_hot).T
            grad = grad.T
            x_adv = x_adv + step_size * np.sign(grad)
            delta = np.clip(x_adv - x, -self.epsilon, self.epsilon)
            x_adv = x + delta
        return x_adv

    def adversarial_training_step(self, x: np.ndarray, y: np.ndarray) -> float:
        x_adv = self.pgd_attack(x, steps=3)
        x_mix = np.vstack([x, x_adv])
        y_mix = np.hstack([y, y])
        probs = self.predict_proba(x_mix)
        loss = -np.mean(np.log(probs[np.arange(len(y_mix)), y_mix] + 1e-9))
        grad_w = x_mix.T @ (probs - np.eye(self.num_classes)[y_mix]) / len(y_mix)
        grad_b = np.mean(probs - np.eye(self.num_classes)[y_mix], axis=0)
        self.weights -= 0.01 * grad_w
        self.bias -= 0.01 * grad_b
        return float(loss)

    def fit_ood_detector(self, clean_inputs: np.ndarray) -> None:
        self.ood_mean = np.mean(clean_inputs, axis=0)
        cov = np.cov(clean_inputs.T)
        cov += 1e-6 * np.eye(cov.shape[0])
        self.ood_cov_inv = np.linalg.inv(cov)
        distances = []
        for x in clean_inputs:
            d = self._mahalanobis(x)
            distances.append(d)
        self.ood_threshold = float(np.percentile(distances, 95))

    def detect_ood(self, x: np.ndarray) -> OODResult:
        if self.ood_mean is None or self.ood_cov_inv is None:
            raise RuntimeError("OOD detector not fitted")
        dist = self._mahalanobis(x)
        dist_val = float(np.asarray(dist).item())
        is_ood = bool(dist > self.ood_threshold)
        confidence = 1.0 / (1.0 + np.exp(-dist_val))
        return OODResult(
            is_ood=is_ood,
            mahalanobis_distance=round(dist_val, 6),
            threshold=round(float(self.ood_threshold), 6),
            confidence=round(confidence, 6),
        )

    def _mahalanobis(self, x: np.ndarray) -> np.ndarray:
        diff = x - self.ood_mean
        product = diff @ self.ood_cov_inv * diff
        if product.ndim == 1:
            return np.sqrt(np.sum(product))
        return np.sqrt(np.sum(product, axis=1))

    def evaluate(self, x_clean: np.ndarray, y_true: np.ndarray, x_adv: Optional[np.ndarray] = None) -> RobustnessReport:
        clean_preds = self.predict(x_clean)
        clean_acc = float(np.mean(clean_preds == y_true))
        adv_acc = clean_acc
        if x_adv is not None:
            adv_preds = self.predict(x_adv)
            adv_acc = float(np.mean(adv_preds == y_true))
        ood_rate = 0.0
        if self.ood_mean is not None:
            ood_results = [self.detect_ood(xi.reshape(1, -1)) for xi in x_clean]
            ood_rate = sum(r.is_ood for r in ood_results) / len(ood_results)
        return RobustnessReport(
            clean_accuracy=round(clean_acc, 4),
            adversarial_accuracy=round(adv_acc, 4),
            robustness_drop=round(clean_acc - adv_acc, 4),
            ood_detection_rate=round(ood_rate, 4),
            passed=adv_acc >= clean_acc * 0.7,
        )
