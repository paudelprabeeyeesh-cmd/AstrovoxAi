
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class Document:
    id: str
    text: str


class CrossEncoderReranker:
    def __init__(self, embedding_dim: int = 64):
        self.embedding_dim = embedding_dim
        self.doc_embeddings: Optional[np.ndarray] = None
        self.doc_ids: List[str] = []

    def index_documents(self, documents: List[Document]) -> None:
        rng = np.random.RandomState(42)
        self.doc_embeddings = rng.randn(len(documents), self.embedding_dim)
        norms = np.linalg.norm(self.doc_embeddings, axis=1, keepdims=True)
        self.doc_embeddings = self.doc_embeddings / np.where(norms == 0, 1e-10, norms)
        self.doc_ids = [doc.id for doc in documents]

    def _encode_query(self, query: str) -> np.ndarray:
        rng = np.random.RandomState(hash(query) % (2**32))
        vec = rng.randn(self.embedding_dim)
        return vec / (np.linalg.norm(vec) + 1e-10)

    def rerank(self, query: str, candidates: List[Tuple[str, float]], top_k: int = 5) -> List[Tuple[str, float]]:
        if not candidates or self.doc_embeddings is None:
            return candidates[:top_k]
        query_vec = self._encode_query(query)
        scores = []
        doc_id_to_idx = {doc_id: idx for idx, doc_id in enumerate(self.doc_ids)}
        for doc_id, _ in candidates:
            idx = doc_id_to_idx.get(doc_id)
            if idx is not None:
                score = float(np.dot(self.doc_embeddings[idx], query_vec))
                scores.append((doc_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
