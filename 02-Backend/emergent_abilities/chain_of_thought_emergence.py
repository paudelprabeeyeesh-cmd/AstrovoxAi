import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional


def _softmax(logits: List[float]) -> List[float]:
    max_logit = max(logits)
    exps = [math.exp(val - max_logit) for val in logits]
    total = sum(exps)
    return [e / total for e in exps]


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _tanh_vec(v: List[float]) -> List[float]:
    return [math.tanh(x) for x in v]


def _matmul_vec(matrix: List[List[float]], vec: List[float]) -> List[float]:
    return [_dot(row, vec) for row in matrix]


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
        self.w_embed: List[List[float]] = [[random.gauss(0, 0.02) for _ in range(hidden_dim)] for _ in range(vocab_size)]
        self.w_step: List[List[float]] = [[random.gauss(0, 0.02) for _ in range(hidden_dim)] for _ in range(hidden_dim)]
        self.w_out: List[List[float]] = [[random.gauss(0, 0.02) for _ in range(vocab_size)] for _ in range(hidden_dim)]
        self.step_embeddings: List[List[float]] = []

    def embed_token(self, token_id: int) -> List[float]:
        safe_id = token_id % self.vocab_size
        one_hot = [1.0 if i == safe_id else 0.0 for i in range(self.vocab_size)]
        return _matmul_vec(_transpose(self.w_embed), one_hot)

    def reasoning_step(self, hidden_state: List[float], step_index: int) -> List[float]:
        new_hidden = _tanh_vec(_matmul_vec(_transpose(self.w_step), hidden_state))
        self.step_embeddings.append(new_hidden)
        return new_hidden

    def generate_chain(self, prompt_tokens: List[int], max_new_tokens: int = 8) -> CoTResult:
        self.step_embeddings = []
        if prompt_tokens:
            token_embs = [self.embed_token(t) for t in prompt_tokens]
            hidden = [sum(xs) / len(xs) for xs in zip(*token_embs)]
        else:
            hidden = [0.0] * self.hidden_dim
        reasoning_chain: List[str] = []
        coherence_scores: List[float] = []
        for step in range(self.max_steps):
            hidden = self.reasoning_step(hidden, step)
            logits = _matmul_vec(_transpose(self.w_out), hidden)
            top_token = logits.index(max(logits))
            raw_conf = max(logits) / (sum(abs(v) for v in logits) + 1e-8)
            coherence_scores.append(max(0.0, min(1.0, raw_conf)))
            reasoning_chain.append(f"Step {step + 1}: token_{top_token}")
            if max_new_tokens > 0 and step >= max_new_tokens - 1:
                break
        answer_logits = _matmul_vec(_transpose(self.w_out), hidden)
        answer_token = answer_logits.index(max(answer_logits))
        confidence = sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0.0
        coherence = sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0.0
        return CoTResult(
            reasoning_chain=reasoning_chain,
            answer=f"token_{answer_token}",
            confidence=confidence,
            num_steps=len(reasoning_chain),
            coherence_score=coherence,
        )

    def compute_scaling_law(self, prompt_lengths: List[int], num_runs: int = 5) -> Dict[str, float]:
        accuracies = []
        for L in prompt_lengths:
            correct = sum(self.generate_chain(list(range(L))).coherence_score > 0.5 for _ in range(num_runs))
            accuracies.append(correct / num_runs)
        xs = list(range(1, len(prompt_lengths) + 1))
        log_xs = [math.log(x) for x in xs]
        log_accs = [math.log(max(a, 1e-8)) for a in accuracies]
        n = len(xs)
        sum_x = sum(log_xs)
        sum_y = sum(log_accs)
        sum_xy = sum(x * y for x, y in zip(log_xs, log_accs))
        sum_x2 = sum(x * x for x in log_xs)
        denom = n * sum_x2 - sum_x * sum_x
        if denom == 0:
            return {"intercept": sum_y / n, "scaling_exponent": 0.0}
        intercept = (sum_y * sum_x2 - sum_x * sum_xy) / denom
        slope = (n * sum_xy - sum_x * sum_y) / denom
        return {"intercept": intercept, "scaling_exponent": slope}


def _transpose(matrix: List[List[float]]) -> List[List[float]]:
    if not matrix:
        return []
    return [[matrix[i][j] for i in range(len(matrix))] for j in range(len(matrix[0]))]


class ReasoningScalingAnalyzer:
    def __init__(self):
        self.step_performance: Dict[int, List[float]] = {k: [] for k in range(1, 17)}

    def record_step_performance(self, num_steps: int, performance: float):
        if num_steps not in self.step_performance:
            self.step_performance[num_steps] = []
        self.step_performance[num_steps].append(performance)

    def scaling_curve(self) -> List[float]:
        return [sum(v) / len(v) if v else 0.0 for v in self.step_performance.values()]

    def diminishing_returns_point(self) -> Optional[int]:
        curve = self.scaling_curve()
        if len(curve) < 3:
            return None
        diffs = [curve[i + 1] - curve[i] for i in range(len(curve) - 1)]
        for i in range(1, len(diffs)):
            if curve[i] > 0 and diffs[i] < 0.01:
                return i + 1
        return None
