"""
Multi-vector retrieval with late interaction and ColBERT-style matching.
"""

from __future__ import annotations

import logging
from typing import Optional, List, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class MultiVectorRetriever(nn.Module):
    def __init__(self, embedding_dim: int = 128, num_vectors: int = 32):
        super().__init__()
        self.embedding_dim = embedding_dim
        self.num_vectors = num_vectors
        self.encoder = nn.Linear(embedding_dim, embedding_dim * num_vectors)

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        B, T, _ = x.shape
        return self.encoder(x).view(B, T, self.num_vectors, self.embedding_dim)

    def score(self, query_vectors: torch.Tensor, doc_vectors: torch.Tensor) -> torch.Tensor:
        B, Tq, Nq, D = query_vectors.shape
        B, Td, Nd, D = doc_vectors.shape
        query_vectors = F.normalize(query_vectors, dim=-1)
        doc_vectors = F.normalize(doc_vectors, dim=-1)
        scores = torch.matmul(query_vectors, doc_vectors.transpose(-2, -1))
        max_scores = scores.max(dim=-1)[0].sum(dim=-1)
        return max_scores

    def retrieve(self, query: torch.Tensor, doc_embeddings: torch.Tensor, top_k: int = 10) -> Tuple[torch.Tensor, torch.Tensor]:
        q_vecs = self.encode(query)
        d_vecs = self.encode(doc_embeddings)
        scores = self.score(q_vecs, d_vecs)
        top_scores, top_indices = torch.topk(scores, k=min(top_k, scores.shape[-1]))
        return top_scores, top_indices
