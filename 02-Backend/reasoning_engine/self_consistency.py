from typing import List, Tuple, Any, Callable
import numpy as np


class SelfConsistency:
    def __init__(
        self,
        generate_fn: Callable[[Any], str],
        num_samples: int = 5,
        similarity_threshold: float = 0.8,
    ):
        self.generate_fn = generate_fn
        self.num_samples = num_samples
        self.similarity_threshold = similarity_threshold

    def generate_multiple_answers(self, query: Any) -> List[str]:
        return [self.generate_fn(query) for _ in range(self.num_samples)]

    def _embed(self, text: str) -> np.ndarray:
        rng = np.random.default_rng(hash(text) % (2**32))
        vec = rng.standard_normal(16)
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec
        return vec / norm

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
            return 0.0
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def semantic_cluster(self, answers: List[str]) -> List[List[str]]:
        embeddings = [self._embed(a) for a in answers]
        clusters = []
        used = set()
        for i in range(len(answers)):
            if i in used:
                continue
            cluster = [answers[i]]
            used.add(i)
            for j in range(i + 1, len(answers)):
                if j in used:
                    continue
                sim = self._cosine_similarity(embeddings[i], embeddings[j])
                if sim >= self.similarity_threshold:
                    cluster.append(answers[j])
                    used.add(j)
            clusters.append(cluster)
        return clusters

    def majority_vote(self, answers: List[str]) -> Tuple[str, float]:
        if not answers:
            return "", 0.0
        counts = {}
        for ans in answers:
            counts[ans] = counts.get(ans, 0) + 1
        best = max(counts, key=counts.get)
        return best, counts[best] / len(answers)

    def run(self, query: Any) -> Tuple[str, float, List[List[str]]]:
        answers = self.generate_multiple_answers(query)
        clusters = self.semantic_cluster(answers)
        largest = max(clusters, key=len) if clusters else []
        majority_answer, confidence = self.majority_vote(largest)
        return majority_answer, confidence, clusters
