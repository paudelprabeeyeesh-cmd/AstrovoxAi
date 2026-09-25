from typing import List, Dict, Any, Tuple
from ASTROVOX_AI.ai_core.memory.memory_importance_scoring import MemoryImportanceScorer


class MemoryRanking:
    def __init__(self, embedding_dim: int = 768):
        self.scorer = MemoryImportanceScorer(embedding_dim)

    def rank(self, memories: List[Dict[str, Any]], embeddings: torch.Tensor, top_k: int = 10, recency_weight: float = 0.3, importance_weight: float = 0.4, relevance_weight: float = 0.3) -> List[Dict[str, Any]]:
        importances = self.scorer.score(embeddings).cpu().tolist()
        recencies = self._compute_recencies(memories)
        relevances = self._compute_relevances(memories)
        combined = []
        for i, mem in enumerate(memories):
            combined_score = (importance_weight * importances[i] + recency_weight * recencies[i] + relevance_weight * relevances[i])
            combined.append({**mem, 'combined_score': combined_score})
        combined.sort(key=lambda x: x.get('combined_score', 0), reverse=True)
        return combined[:top_k]

    def _compute_recencies(self, memories: List[Dict[str, Any]]) -> List[float]:
        now = datetime.now()
        recencies = []
        for mem in memories:
            last_accessed = mem.get('last_accessed', now.isoformat())
            age_days = (now - datetime.fromisoformat(last_accessed)).total_seconds() / 86400.0
            recencies.append(1.0 / (1.0 + age_days))
        max_recency = max(recencies) if recencies else 1.0
        return [r / max_recency for r in recencies]

    def _compute_relevances(self, memories: List[Dict[str, Any]]) -> List[float]:
        return [mem.get('relevance_score', 0.5) for mem in memories]
