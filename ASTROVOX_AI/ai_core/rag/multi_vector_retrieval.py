from typing import List, Dict, Any, Tuple
import torch
import torch.nn as nn


class MultiVectorRetriever:
    def __init__(self, embedding_dim: int = 768, num_vectors: int = 4):
        self.embedding_dim = embedding_dim
        self.num_vectors = num_vectors
        self.proj = nn.Linear(embedding_dim, embedding_dim * num_vectors)
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.vector_index: List[Tuple[torch.Tensor, str]] = []

    def encode(self, text_embedding: torch.Tensor) -> torch.Tensor:
        projected = self.proj(text_embedding)
        return projected.view(self.num_vectors, self.embedding_dim)

    def add_document(self, doc_id: str, text: str, embedding: torch.Tensor) -> None:
        self.documents[doc_id] = {'text': text, 'embedding': embedding}
        vectors = self.encode(embedding)
        for vec in vectors:
            self.vector_index.append((vec.detach(), doc_id))

    def retrieve(self, query_embedding: torch.Tensor, top_k: int = 5) -> List[Dict[str, Any]]:
        query_vectors = self.encode(query_embedding)
        scores = []
        for doc_id, data in self.documents.items():
            doc_vectors = self.encode(data['embedding'])
            score = torch.max(torch.mm(query_vectors, doc_vectors.t())).item()
            scores.append((score, doc_id, data['text']))
        scores.sort(key=lambda x: x[0], reverse=True)
        return [{'doc_id': doc_id, 'text': text, 'score': score} for score, doc_id, text in scores[:top_k]]
