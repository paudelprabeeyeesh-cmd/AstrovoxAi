import json
import logging
from typing import Optional
from .run import GoldenSetEvaluator

logger = logging.getLogger(__name__)


class RAGEvaluator:
    def __init__(self):
        self.evaluator = GoldenSetEvaluator()
    
    def precision_at_k(self, retrieved: list[dict], relevant_ids: list[str], k: int = 5) -> float:
        if not retrieved or not relevant_ids:
            return 0.0
        top_k = retrieved[:k]
        relevant_in_top_k = sum(1 for doc in top_k if doc.get("id") in relevant_ids)
        return relevant_in_top_k / min(k, len(top_k))
    
    def recall_at_k(self, retrieved: list[dict], relevant_ids: list[str], k: int = 5) -> float:
        if not relevant_ids:
            return 0.0
        top_k = retrieved[:k]
        relevant_in_top_k = sum(1 for doc in top_k if doc.get("id") in relevant_ids)
        return relevant_in_top_k / len(relevant_ids)
    
    def answer_relevance(self, query: str, answer: str) -> float:
        query_terms = set(query.lower().split())
        answer_terms = set(answer.lower().split())
        if not query_terms:
            return 0.0
        overlap = len(query_terms & answer_terms)
        return overlap / len(query_terms)
    
    def evaluate_query(self, query: str, retrieved: list[dict], answer: str, relevant_ids: list[str]) -> dict:
        precision = self.precision_at_k(retrieved, relevant_ids)
        recall = self.recall_at_k(retrieved, relevant_ids)
        relevance = self.answer_relevance(query, answer)
        
        return {
            "query": query,
            "precision@5": round(precision, 3),
            "recall@5": round(recall, 3),
            "answer_relevance": round(relevance, 3),
        }
    
    def log_metrics(self, metrics: dict):
        logger.info(f"RAG_METRICS: {json.dumps(metrics)}")
