
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Callable, Optional


@dataclass
class Document:
    id: str
    text: str
    embedding: np.ndarray
    metadata: dict = field(default_factory=dict)


class HopResult:
    def __init__(self, documents: List[Document], query: str):
        self.documents = documents
        self.query = query


class MultiHopRetriever:
    def __init__(self, embedding_dim: int = 64):
        self.embedding_dim = embedding_dim
        self.documents: List[Document] = []

    def add_documents(self, documents: List[Document]) -> None:
        self.documents.extend(documents)

    def _retrieve(self, query: str, k: int = 3) -> List[Document]:
        rng = np.random.RandomState(hash(query) % (2**32))
        if not self.documents:
            return []
        query_vec = rng.randn(self.embedding_dim)
        query_vec = query_vec / (np.linalg.norm(query_vec) + 1e-10)
        doc_vecs = []
        for doc in self.documents:
            v = doc.embedding / (np.linalg.norm(doc.embedding) + 1e-10)
            doc_vecs.append(v)
        doc_vecs = np.array(doc_vecs)
        scores = doc_vecs @ query_vec
        top_k = min(k, len(self.documents))
        indices = np.argsort(-scores)[:top_k]
        return [self.documents[i] for i in indices]

    def synthesize(self, original_query: str, hop_results: List[HopResult]) -> str:
        return f"Synthesized answer for: {original_query}"

    def retrieve(self, original_query: str, num_hops: int = 2, k: int = 3, synthesis_fn: Optional[Callable] = None) -> Tuple[List[Document], str]:
        current_query = original_query
        all_docs = []
        results = []
        for _ in range(num_hops):
            docs = self._retrieve(current_query, k=k)
            all_docs.extend(docs)
            results.append(HopResult(documents=docs, query=current_query))
            current_query = f"{original_query} context {' '.join(d.text for d in docs)}"
        answer = synthesis_fn(original_query, results) if synthesis_fn else self.synthesize(original_query, results)
        return all_docs, answer
