import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ICLResult:
    predicted_token: int
    confidence: float
    task_confidence: float
    in_context_benefit: float


class InContextLearningModel:
    def __init__(self, vocab_size: int, embedding_dim: int, num_heads: int):
        self.vocab_size = vocab_size
        self.embedding_dim = embedding_dim
        self.num_heads = num_heads
        self.W_K = np.random.randn(embedding_dim, embedding_dim) * 0.02
        self.W_V = np.random.randn(embedding_dim, vocab_size) * 0.02
        self.W_Q = np.random.randn(embedding_dim, embedding_dim) * 0.02

    def attention(self, query: np.ndarray, key: np.ndarray, value: np.ndarray) -> np.ndarray:
        d_k = key.shape[-1]
        scores = query @ key.T / np.sqrt(d_k)
        weights = np.exp(scores - np.max(scores, axis=-1, keepdims=True))
        weights = weights / np.sum(weights, axis=-1, keepdims=True)
        return weights @ value

    def forward(self, context_embeddings: np.ndarray, query_embedding: np.ndarray) -> np.ndarray:
        key = context_embeddings @ self.W_K
        value = context_embeddings @ self.W_V
        query = query_embedding @ self.W_Q
        return self.attention(query, key, value)

    def predict(self, context_examples: List[Tuple[np.ndarray, int]], query_input: np.ndarray) -> ICLResult:
        if not context_examples:
            rand_pred = np.random.randint(0, self.vocab_size)
            return ICLResult(predicted_token=rand_pred, confidence=0.0, task_confidence=0.0, in_context_benefit=0.0)
        ctx_inputs = np.array([ex[0] for ex in context_examples])
        ctx_embs = ctx_inputs / (np.linalg.norm(ctx_inputs, axis=-1, keepdims=True) + 1e-8)
        query_norm = query_input / (np.linalg.norm(query_input) + 1e-8)
        logits = self.forward(ctx_embs, query_norm)
        probs = np.exp(logits - np.max(logits))
        probs = probs / (np.sum(probs) + 1e-8)
        confidence = float(np.max(probs))
        token = int(np.argmax(probs))
        if len(context_examples) >= 2:
            ctx_labels = np.array([ex[1] for ex in context_examples])
            consistency = float(np.mean(ctx_labels == ctx_labels[0]))
            task_confidence = consistency * confidence
        else:
            task_confidence = confidence * 0.5
        benefit = min(1.0, len(context_examples) * 0.15)
        return ICLResult(predicted_token=token, confidence=confidence, task_confidence=task_confidence, in_context_benefit=benefit)


class TaskIdentifier:
    def __init__(self, num_tasks: int = 5):
        self.num_tasks = num_tasks
        self.task_prototypes: Dict[int, np.ndarray] = {}

    def identify_task(self, context_examples: List[Tuple[np.ndarray, int]], query_input: np.ndarray) -> int:
        if not self.task_prototypes:
            return 0
        query_norm = query_input / (np.linalg.norm(query_input) + 1e-8)
        best_task, best_sim = 0, -1.0
        for task_id, prototype in self.task_prototypes.items():
            sim = float(np.dot(query_norm, prototype))
            if sim > best_sim:
                best_sim, best_task = sim, task_id
        return best_task

    def update_task_prototype(self, task_id: int, embedding: np.ndarray):
        if task_id not in self.task_prototypes:
            self.task_prototypes[task_id] = embedding.copy()
        else:
            self.task_prototypes[task_id] = 0.9 * self.task_prototypes[task_id] + 0.1 * embedding


class ICLDynamicsAnalyzer:
    def __init__(self):
        self.shot_performance: Dict[int, List[float]] = {k: [] for k in range(0, 11)}

    def record_performance(self, num_shots: int, performance: float):
        self.shot_performance[num_shots].append(performance)

    def learning_curve(self) -> np.ndarray:
        return np.array([np.mean(v) if v else 0.0 for v in self.shot_performance.values()])

    def sensitivity_to_context(self) -> float:
        curve = self.learning_curve()
        return float(np.std(curve))
