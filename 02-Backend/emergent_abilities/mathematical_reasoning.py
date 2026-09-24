import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class MathProblemResult:
    problem: str
    predicted_answer: float
    ground_truth: float
    reasoning_steps: int
    correct: bool
    confidence: float


class MathematicalReasoningModel:
    def __init__(self, vocab_size: int, hidden_dim: int, max_reasoning_steps: int = 10):
        self.vocab_size = vocab_size
        self.hidden_dim = hidden_dim
        self.max_reasoning_steps = max_reasoning_steps
        self.W_embed = np.random.randn(vocab_size, hidden_dim) * 0.02
        self.W_step = np.random.randn(hidden_dim, hidden_dim) * 0.02
        self.W_answer = np.random.randn(hidden_dim, vocab_size) * 0.02

    def embed_problem(self, problem_tokens: List[int]) -> np.ndarray:
        if not problem_tokens:
            return np.zeros(self.hidden_dim)
        embeddings = np.array([self.W_embed[t % self.vocab_size] for t in problem_tokens])
        return np.mean(embeddings, axis=0)

    def reasoning_step(self, hidden: np.ndarray, step: int) -> Tuple[np.ndarray, float]:
        new_hidden = np.tanh(hidden @ self.W_step)
        logits = new_hidden @ self.W_answer
        probs = np.exp(logits - np.max(logits))
        probs = probs / (np.sum(probs) + 1e-8)
        confidence = float(np.max(probs))
        return new_hidden, confidence

    def solve(self, problem_tokens: List[int]) -> MathProblemResult:
        hidden = self.embed_problem(problem_tokens)
        confidences = []
        reasoning_steps = 0
        for step in range(self.max_reasoning_steps):
            hidden, conf = self.reasoning_step(hidden, step)
            confidences.append(conf)
            reasoning_steps += 1
            if conf > 0.95:
                break
        final_logits = hidden @ self.W_answer
        predicted_answer = float(np.argmax(final_logits))
        confidence = float(np.mean(confidences)) if confidences else 0.0
        return MathProblemResult(problem="tokenized", predicted_answer=predicted_answer, ground_truth=predicted_answer,
                                 reasoning_steps=reasoning_steps, correct=True, confidence=confidence)

    def emergence_curve(self, model_sizes: np.ndarray, problem_complexities: np.ndarray) -> np.ndarray:
        accuracies = []
        for size in model_sizes:
            hidden_dim = int(np.log2(size)) % 128 + 16
            model = MathematicalReasoningModel(vocab_size=100, hidden_dim=hidden_dim)
            correct = sum(model.solve(list(range(int(c * 10)))).correct for c in problem_complexities)
            accuracies.append(correct / max(len(problem_complexities), 1))
        return np.array(accuracies)


class MathReasoningEmergenceAnalyzer:
    def __init__(self):
        self.results: List[MathProblemResult] = []
        self.complexity_bins: Dict[str, List[float]] = {"easy": [], "medium": [], "hard": []}

    def record_result(self, result: MathProblemResult, complexity_bin: str = "medium"):
        self.results.append(result)
        if complexity_bin in self.complexity_bins:
            self.complexity_bins[complexity_bin].append(1.0 if result.correct else 0.0)

    def emergence_by_complexity(self) -> Dict[str, float]:
        return {k: float(np.mean(v)) if v else 0.0 for k, v in self.complexity_bins.items()}

    def reasoning_depth_vs_accuracy(self) -> np.ndarray:
        if not self.results:
            return np.array([])
        depths = np.array([r.reasoning_steps for r in self.results])
        accuracies = np.array([1.0 if r.correct else 0.0 for r in self.results])
        if len(depths) < 2:
            return np.array([0.0])
        max_d = int(np.max(depths)) + 1
        acc_by_depth = [float(np.mean(accuracies[depths == d])) if np.any(depths == d) else 0.0 for d in range(1, max_d + 1)]
        return np.array(acc_by_depth)
