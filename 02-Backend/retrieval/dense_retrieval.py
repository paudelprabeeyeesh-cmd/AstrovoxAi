
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Document:
    id: str
    text: str
    embedding: np.ndarray
    metadata: dict = field(default_factory=dict)


class HNSWIndex:
    def __init__(self, embedding_dim: int, ef_search: int = 50, ef_construction: int = 100, M: int = 16):
        self.embedding_dim = embedding_dim
        self.ef_search = ef_search
        self.ef_construction = ef_construction
        self.M = M
        self.documents: List[Document] = []
        self.embeddings: Optional[np.ndarray] = None

    def add_document(self, document: Document) -> None:
        self.documents.append(document)

    def build(self) -> None:
        if not self.documents:
            return
        self.embeddings = np.array([doc.embedding for doc in self.documents])
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1e-10, norms)
        self.embeddings = self.embeddings / norms

    def _cosine_similarity(self, query: np.ndarray) -> np.ndarray:
        if self.embeddings is None or len(self.documents) == 0:
            return np.array([])
        return self.embeddings @ query

    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[tuple]:
        if self.embeddings is None or len(self.documents) == 0:
            return []
        query = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)
        scores = self._cosine_similarity(query)
        top_k = min(k, len(self.documents))
        indices = np.argsort(-scores)[:top_k]
        return [(self.documents[i].id, float(scores[i])) for i in indices]


class DenseRetriever:
    def __init__(self, embedding_dim: int = 128):
        self.index = HNSWIndex(embedding_dim=embedding_dim)
        self.embedding_dim = embedding_dim

    def add_documents(self, documents: List[Document]) -> None:
        for doc in documents:
            if doc.embedding.shape[-1] != self.embedding_dim:
                doc.embedding = np.zeros(self.embedding_dim)
            self.index.add_document(doc)
        self.index.build()

    def embed_query(self, query_text: str) -> np.ndarray:
        return np.random.RandomState(hash(query_text) % (2**32)).randn(self.embedding_dim)

    def search(self, query_text: str, k: int = 5) -> List[tuple]:
        query_embedding = self.embed_query(query_text)
        return self.index.search(query_embedding, k=k)
