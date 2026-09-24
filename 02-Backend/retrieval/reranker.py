from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Document:
    id: str
    text: str


class Reranker:
    def __init__(self):
        self.documents: List[Document] = []

    def index_documents(self, documents: List[Document]) -> None:
        self.documents = documents

    def _jaccard(self, query: str, text: str) -> float:
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        intersection = query_words & text_words
        union = query_words | text_words
        return len(intersection) / len(union) if union else 0.0

    def rerank(self, query: str, candidates: List[Tuple[str, float]], top_k: int = 5) -> List[Tuple[str, float]]:
        if not candidates or not self.documents:
            return candidates[:top_k]
        doc_map = {doc.id: doc for doc in self.documents}
        scores = []
        for doc_id, _ in candidates:
            doc = doc_map.get(doc_id)
            if doc is not None:
                score = self._jaccard(query, doc.text)
                scores.append((doc_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
