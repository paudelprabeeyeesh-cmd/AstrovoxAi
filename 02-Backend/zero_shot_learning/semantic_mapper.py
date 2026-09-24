from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Concept:
    name: str
    attributes: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None


class SemanticMapper:
    def __init__(self, dim: int = 32):
        self.dim = dim
        self._concepts: Dict[str, Concept] = {}
        self._vocab: Dict[str, int] = {}
        self._next_idx = 0

    def _ensure_token(self, token: str) -> int:
        if token not in self._vocab:
            self._vocab[token] = self._next_idx
            self._next_idx += 1
        return self._vocab[token]

    def add_concept(self, name: str, attributes: Optional[List[str]] = None) -> Concept:
        concept = Concept(name=name, attributes=attributes or [])
        concept.embedding = self._embed_text(" ".join([name] + (attributes or [])))
        self._concepts[name] = concept
        return concept

    def _embed_text(self, text: str) -> List[float]:
        tokens = [t.lower() for t in text.split() if t.strip()]
        vec = [0.0] * self.dim
        for tok in tokens:
            idx = self._ensure_token(tok)
            pos = idx % self.dim
            vec[pos] += 1.0
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def similarity(self, a: str, b: str) -> float:
        ca = self._concepts.get(a)
        cb = self._concepts.get(b)
        if ca is None or cb is None or ca.embedding is None or cb.embedding is None:
            return 0.0
        return sum(x * y for x, y in zip(ca.embedding, cb.embedding))

    def nearest(self, query: str, k: int = 1) -> List[Tuple[str, float]]:
        q_emb = self._embed_text(query)
        scores = []
        for name, concept in self._concepts.items():
            if concept.embedding is None:
                continue
            score = sum(x * y for x, y in zip(q_emb, concept.embedding))
            scores.append((name, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]

    def get_concept(self, name: str) -> Optional[Concept]:
        return self._concepts.get(name)

    def list_concepts(self) -> List[str]:
        return list(self._concepts.keys())
