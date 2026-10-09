from typing import List, Tuple, Dict


class HybridSearch:
    def __init__(self, retrievers: List[object], weights: List[float] = None):
        self.retrievers = retrievers
        self.weights = weights or [1.0] * len(retrievers)

    def search(self, query: str, k: int = 5) -> List[Tuple[str, float]]:
        candidate_scores: Dict[str, float] = {}
        for retriever, weight in zip(self.retrievers, self.weights):
            results = retriever.search(query, k=k * 2)
            for doc_id, score in results:
                candidate_scores[doc_id] = candidate_scores.get(doc_id, 0.0) + weight * score
        ranked = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:k]
