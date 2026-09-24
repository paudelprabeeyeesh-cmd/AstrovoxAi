import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


def _softmax(logits: List[float]) -> List[float]:
    max_logit = max(logits)
    exps = [math.exp(val - max_logit) for val in logits]
    total = sum(exps)
    return [e / total for e in exps]


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(v: List[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _normalize(v: List[float]) -> List[float]:
    n = _norm(v)
    if n == 0:
        return [0.0] * len(v)
    return [x / n for x in v]


def _matmul_vec(matrix: List[List[float]], vec: List[float]) -> List[float]:
    return [_dot(row, vec) for row in matrix]


def _transpose(matrix: List[List[float]]) -> List[List[float]]:
    if not matrix:
        return []
    return [[matrix[i][j] for i in range(len(matrix))] for j in range(len(matrix[0]))]


def _attention(query: List[float], keys: List[List[float]], values: List[List[float]]) -> List[float]:
    d_k = len(keys[0]) if keys else 1
    scores = [_dot(query, k) / math.sqrt(d_k) for k in keys]
    max_s = max(scores)
    exps = [math.exp(s - max_s) for s in scores]
    total = sum(exps)
    weights = [e / total for e in exps]
    dim = len(values[0]) if values else 0
    result = [0.0] * dim
    for w, v in zip(weights, values):
        for j in range(dim):
            result[j] += w * v[j]
    return result


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
        self.w_k: List[List[float]] = [[random.gauss(0, 0.02) for _ in range(embedding_dim)] for _ in range(embedding_dim)]
        self.w_v: List[List[float]] = [[random.gauss(0, 0.02) for _ in range(vocab_size)] for _ in range(embedding_dim)]
        self.w_q: List[List[float]] = [[random.gauss(0, 0.02) for _ in range(embedding_dim)] for _ in range(embedding_dim)]

    def forward(self, context_embeddings: List[List[float]], query_embedding: List[float]) -> List[float]:
        keys = _transpose([_matmul_vec(_transpose(self.w_k), emb) for emb in context_embeddings])
        values = [_matmul_vec(_transpose(self.w_v), emb) for emb in context_embeddings]
        query = _matmul_vec(_transpose(self.w_q), query_embedding)
        return _attention(query, _transpose(keys), values)

    def predict(self, context_examples: List[Tuple[List[float], int]], query_input: List[float]) -> ICLResult:
        if not context_examples:
            return ICLResult(
                predicted_token=random.randint(0, self.vocab_size - 1),
                confidence=0.0,
                task_confidence=0.0,
                in_context_benefit=0.0,
            )
        ctx_inputs = [ex[0] for ex in context_examples]
        ctx_embs = [_normalize(ci) for ci in ctx_inputs]
        query_norm = _normalize(query_input)
        logits = self.forward(ctx_embs, query_norm)
        probs = _softmax(logits)
        confidence = max(probs)
        token = probs.index(confidence)
        if len(context_examples) >= 2:
            ctx_labels = [ex[1] for ex in context_examples]
            consistency = sum(1 for label in ctx_labels if label == ctx_labels[0]) / len(ctx_labels)
            task_confidence = consistency * confidence
        else:
            task_confidence = confidence * 0.5
        benefit = min(1.0, len(context_examples) * 0.15)
        return ICLResult(
            predicted_token=token,
            confidence=confidence,
            task_confidence=task_confidence,
            in_context_benefit=benefit,
        )


class TaskIdentifier:
    def __init__(self, num_tasks: int = 5):
        self.num_tasks = num_tasks
        self.task_prototypes: Dict[int, List[float]] = {}

    def identify_task(self, context_examples: List[Tuple[List[float], int]], query_input: List[float]) -> int:
        if not self.task_prototypes:
            return 0
        query_norm = _normalize(query_input)
        best_task, best_sim = 0, -1.0
        for task_id, prototype in self.task_prototypes.items():
            sim = _dot(query_norm, prototype)
            if sim > best_sim:
                best_sim, best_task = sim, task_id
        return best_task

    def update_task_prototype(self, task_id: int, embedding: List[float]):
        emb_norm = _normalize(embedding)
        if task_id not in self.task_prototypes:
            self.task_prototypes[task_id] = emb_norm.copy()
        else:
            existing = self.task_prototypes[task_id]
            self.task_prototypes[task_id] = [0.9 * e + 0.1 * n for e, n in zip(existing, emb_norm)]


class ICLDynamicsAnalyzer:
    def __init__(self):
        self.shot_performance: Dict[int, List[float]] = {k: [] for k in range(0, 11)}

    def record_performance(self, num_shots: int, performance: float):
        self.shot_performance[num_shots].append(performance)

    def learning_curve(self) -> List[float]:
        return [sum(v) / len(v) if v else 0.0 for v in self.shot_performance.values()]

    def sensitivity_to_context(self) -> float:
        curve = self.learning_curve()
        mean = sum(curve) / len(curve)
        variance = sum((x - mean) ** 2 for x in curve) / len(curve)
        return math.sqrt(variance)
