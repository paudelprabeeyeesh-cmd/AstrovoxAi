import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class CoTResult:
    reasoning_chain: List[str]
    answer: str
    confidence: float
    num_steps: int
    coherence_score: float


class ChainOfThoughtModel:
    def __init__(self, vocab_size: int, hidden_dim: int, max_steps: int = 8):
        self.vocab_size = vocab_size
        self.hidden_dim = hidden_dim
        self.max_steps = max_steps
        self.W_embed = np.random.randn(vocab_size, hidden_dim) * 0.02
        self.W_step = np.random.randn(hidden_dim, hidden_dim) * 0.02
        self.W_out = np.random.randn(hidden_dim, vocab_size) * 0.02
        self.step_embeddings: List[np.ndarray] = []

    def embed_token(self, token_id: int) -> np.ndarray:
        safe_id = token_id % self.vocab_size
        one_hot = np.zeros(self.vocab_size)
        one_hot[safe_id] = 1.0
        return one_hot @ self.W_embed

    def reasoning_step(self, hidden_state: np.ndarray, step_index: int) -> np.ndarray:
        new_hidden = np.tanh(hidden_state @ self.W_step)
        self.step_embeddings.append(new_hidden)
        return new_hidden

    def generate_chain(self, prompt_tokens: List[int], max_new_tokens: int = 8) -> CoTResult:
        self.step_embeddings = []
        hidden = np.mean([self.embed_token(t) for t in prompt_tokens], axis=0) if prompt_tokens else np.zeros(self.hidden_dim)
        reasoning_chain = []
        coherence_scores = []
        for step in range(self.max_steps):
            hidden = self.reasoning_step(hidden, step)
            logits = hidden @ self.W_out
            top_token = int(np.argmax(logits))
            raw_conf = float(np.max(logits) / (np.sum(logits) + 1e-8))
            coherence_scores.append(max(0.0, min(1.0, raw_conf)))
            reasoning_chain.append(f"Step {step + 1}: token_{top_token}")
            if max_new_tokens > 0 and step >= max_new_tokens - 1:
                break
        answer_token = int(np.argmax(hidden @ self.W_out))
        confidence = float(np.mean(coherence_scores)) if coherence_scores else 0.0
        coherence = float(np.mean(coherence_scores)) if coherence_scores else 0.0
        return CoTResult(reasoning_chain=reasoning_chain, answer=f"token_{answer_token}", confidence=confidence,
                         num_steps=len(reasoning_chain), coherence_score=coherence)

    def compute_scaling_law(self, prompt_lengths: List[int], num_runs: int = 5) -> Dict[str, float]:
        accuracies = []
        for L in prompt_lengths:
            correct = sum(self.generate_chain(list(range(L))).coherence_score > 0.5 for _ in range(num_runs))
            accuracies.append(correct / num_runs)
        A = np.column_stack([np.ones(len(prompt_lengths)), np.log(np.array(prompt_lengths))])
        coeffs, _, _, _ = np.linalg.lstsq(A, np.log(np.array(accuracies) + 1e-8), rcond=None)
        return {"intercept": float(coeffs[0]), "scaling_exponent": float(coeffs[1])}


class ReasoningScalingAnalyzer:
    def __init__(self):
        self.step_performance: Dict[int, List[float]] = {k: [] for k in range(1, 17)}

    def record_step_performance(self, num_steps: int, performance: float):
        if num_steps not in self.step_performance:
            self.step_performance[num_steps] = []
        self.step_performance[num_steps].append(performance)

    def scaling_curve(self) -> np.ndarray:
        return np.array([np.mean(v) if v else 0.0 for v in self.step_performance.values()])

    def diminishing_returns_point(self) -> Optional[int]:
        curve = self.scaling_curve()
        if len(curve) < 3:
            return None
        diffs = np.diff(curve)
        for i in range(1, len(diffs)):
            if curve[i] > 0 and diffs[i] < 0.01:
                return i + 1
        return None
