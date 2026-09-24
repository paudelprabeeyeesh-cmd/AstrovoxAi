from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class Concept:
    name: str
    embedding: np.ndarray
    confidence: float
    source: str
    domain: str = "general"


class OpenWorldLearner:
    def __init__(self, embedding_dim: int = 32):
        self.embedding_dim = embedding_dim
        self.concepts: Dict[str, Concept] = {}
        self.transfer_matrix: np.ndarray = np.eye(embedding_dim)

    def learn_concept(self, name: str, domain: str, source: str = "experience") -> Concept:
        emb = self._embed(name)
        concept = Concept(name=name, embedding=emb, confidence=0.5, source=source, domain=domain)
        self.concepts[name] = concept
        return concept

    def _embed(self, name: str) -> np.ndarray:
        vec = np.zeros(self.embedding_dim)
        tokens = name.lower().split()
        for i, token in enumerate(tokens):
            idx = hash(token) % self.embedding_dim
            vec[idx] += 1.0 / (i + 1)
        return vec / max(np.linalg.norm(vec), 1e-6)

    def transfer(self, source_concept: str, target_domain: str) -> Optional[Concept]:
        if source_concept not in self.concepts:
            return None
        sc = self.concepts[source_concept]
        emb = self.transfer_matrix @ sc.embedding
        name = f"transferred_{source_concept}_{target_domain}"
        concept = Concept(name=name, embedding=emb, confidence=sc.confidence * 0.8, source="transfer", domain=target_domain)
        self.concepts[name] = concept
        return concept

    def generalize(self, concept_names: List[str]) -> np.ndarray:
        embs = [self.concepts[n].embedding for n in concept_names if n in self.concepts]
        if not embs:
            return np.zeros(self.embedding_dim)
        general = np.mean(embs, axis=0)
        return general / max(np.linalg.norm(general), 1e-6)

    def query(self, name: str, threshold: float = 0.7) -> List[str]:
        if name not in self.concepts:
            return []
        target = self.concepts[name].embedding
        matches = []
        for n, c in self.concepts.items():
            if n == name:
                continue
            sim = float(np.dot(target, c.embedding))
            if sim > threshold:
                matches.append(n)
        return matches
