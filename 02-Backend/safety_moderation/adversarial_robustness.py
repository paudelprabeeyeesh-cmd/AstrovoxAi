import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class AdversarialExample:
    text: str
    perturbation_type: str
    perturbation_magnitude: float
    original_prediction: str
    adversarial_prediction: str
    robustness_score: float
    passed: bool


class AdversarialRobustnessTester:
    def __init__(self, embed_dim: int = 32, vocab_size: int = 500, epsilon: float = 0.1):
        self.embed_dim = embed_dim
        self.vocab_size = vocab_size
        self.epsilon = epsilon
        np.random.seed(55)
        self.vocab_embeddings = np.random.randn(self.vocab_size, self.embed_dim).astype(np.float64)
        self.classifier_weights = np.random.randn(self.embed_dim, 4).astype(np.float64)
        self.classifier_biases = np.random.randn(4).astype(np.float64)
        self.categories = ["safe", "cbrn", "child_safety", "harassment"]

    def _token_embedding(self, token: str) -> np.ndarray:
        idx = hash(token) % self.vocab_size
        return self.vocab_embeddings[idx]

    def _text_embedding(self, text: str) -> np.ndarray:
        tokens = text.lower().split()[:20]
        if not tokens:
            return np.zeros(self.embed_dim, dtype=np.float64)
        embs = [self._token_embedding(t) for t in tokens]
        emb = np.mean(embs, axis=0)
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        return emb

    def _predict(self, embedding: np.ndarray) -> Tuple[str, float, np.ndarray]:
        logits = embedding @ self.classifier_weights + self.classifier_biases
        probs = np.exp(logits - np.max(logits))
        probs = probs / np.sum(probs)
        idx = int(np.argmax(probs))
        return self.categories[idx], float(probs[idx]), probs

    def fgsm_attack(self, text: str, target_category: Optional[str] = None) -> AdversarialExample:
        original_emb = self._text_embedding(text)
        orig_pred, orig_conf, orig_probs = self._predict(original_emb)
        if target_category is None:
            target_idx = (self.categories.index(orig_pred) + 1) % len(self.categories)
        else:
            target_idx = self.categories.index(target_category)
        one_hot = np.zeros(len(self.categories), dtype=np.float64)
        one_hot[target_idx] = 1.0
        grad = self.classifier_weights @ (orig_probs - one_hot)
        perturbation = self.epsilon * np.sign(grad)
        if np.linalg.norm(perturbation) > self.epsilon:
            perturbation = perturbation / np.linalg.norm(perturbation) * self.epsilon
        adv_emb = original_emb + perturbation
        norm = np.linalg.norm(adv_emb)
        if norm > 0:
            adv_emb = adv_emb / norm
        adv_pred, adv_conf, _ = self._predict(adv_emb)
        perturbation_magnitude = float(np.linalg.norm(adv_emb - original_emb))
        robustness = float(np.linalg.norm(original_emb - adv_emb))
        passed = adv_pred == orig_pred
        return AdversarialExample(
            text=text,
            perturbation_type="fgsm",
            perturbation_magnitude=perturbation_magnitude,
            original_prediction=orig_pred,
            adversarial_prediction=adv_pred,
            robustness_score=robustness,
            passed=passed,
        )

    def pgd_attack(self, text: str, steps: int = 5, step_size: float = 0.02) -> AdversarialExample:
        original_emb = self._text_embedding(text)
        orig_pred, _, orig_probs = self._predict(original_emb)
        adv_emb = original_emb.copy()
        for _ in range(steps):
            logits = adv_emb @ self.classifier_weights + self.classifier_biases
            probs = np.exp(logits - np.max(logits))
            probs = probs / np.sum(probs)
            target_idx = (self.categories.index(orig_pred) + 1) % len(self.categories)
            one_hot = np.zeros(len(self.categories), dtype=np.float64)
            one_hot[target_idx] = 1.0
            grad = self.classifier_weights @ (probs - one_hot)
            adv_emb = adv_emb + step_size * np.sign(grad)
            delta = adv_emb - original_emb
            if np.linalg.norm(delta) > self.epsilon:
                delta = delta / np.linalg.norm(delta) * self.epsilon
            adv_emb = original_emb + delta
            norm = np.linalg.norm(adv_emb)
            if norm > 0:
                adv_emb = adv_emb / norm
        adv_pred, _, _ = self._predict(adv_emb)
        perturbation_magnitude = float(np.linalg.norm(adv_emb - original_emb))
        robustness = float(np.linalg.norm(original_emb - adv_emb))
        passed = adv_pred == orig_pred
        return AdversarialExample(
            text=text,
            perturbation_type="pgd",
            perturbation_magnitude=perturbation_magnitude,
            original_prediction=orig_pred,
            adversarial_prediction=adv_pred,
            robustness_score=robustness,
            passed=passed,
        )

    def long_tail_coverage(self, texts: List[str], quantile: float = 0.1) -> Dict[str, float]:
        robustness_scores = []
        for text in texts:
            example = self.fgsm_attack(text)
            robustness_scores.append(example.robustness_score)
        if len(robustness_scores) == 0:
            return {
                "tail_threshold": 0.0,
                "tail_coverage": 0.0,
                "mean_robustness": 0.0,
                "std_robustness": 0.0,
                "min_robustness": 0.0,
                "max_robustness": 0.0,
                "count": 0.0,
            }
        arr = np.array(robustness_scores, dtype=np.float64)
        tail_threshold = float(np.quantile(arr, quantile))
        tail_covered = float(np.sum(arr <= tail_threshold)) / len(arr)
        return {
            "tail_threshold": tail_threshold,
            "tail_coverage": tail_covered,
            "mean_robustness": float(np.mean(arr)),
            "std_robustness": float(np.std(arr)),
            "min_robustness": float(np.min(arr)),
            "max_robustness": float(np.max(arr)),
        }
