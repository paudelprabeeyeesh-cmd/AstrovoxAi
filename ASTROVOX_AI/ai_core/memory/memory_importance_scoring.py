from typing import List, Dict, Any, Optional, Tuple
import torch
import torch.nn as nn


class MemoryImportanceScorer:
    def __init__(self, embedding_dim: int = 768, hidden_dim: int = 256):
        self.scorer = nn.Sequential(nn.Linear(embedding_dim, hidden_dim), nn.ReLU(), nn.Linear(hidden_dim, 1))

    def score(self, memories: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(self.scorer(memories)).squeeze(-1)

    def rank_memories(self, memories: List[Dict[str, Any]], embeddings: torch.Tensor) -> List[Tuple[Dict[str, Any], float]]:
        scores = self.score(embeddings).cpu().tolist()
        scored = list(zip(memories, scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
