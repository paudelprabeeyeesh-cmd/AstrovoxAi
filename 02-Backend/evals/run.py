import json
import logging
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class GoldenSetEvaluator:
    def __init__(self, golden_set_path: str = "evals/golden.jsonl"):
        self.golden_set_path = golden_set_path
        self.baseline_score = None
    
    def load_golden_set(self) -> list[dict]:
        cases = []
        try:
            with open(self.golden_set_path, "r") as f:
                for line in f:
                    cases.append(json.loads(line.strip()))
        except FileNotFoundError:
            logger.warning("Golden set not found")
        return cases
    
    def evaluate_response(self, case: dict, response: str) -> dict:
        scores = {
            "relevance": self._score_relevance(case.get("query", ""), response),
            "accuracy": self._score_accuracy(case.get("expected", ""), response),
            "safety": self._score_safety(response),
        }
        overall = sum(scores.values()) / len(scores)
        return {"case_id": case.get("id"), "scores": scores, "overall": overall}
    
    def _score_relevance(self, query: str, response: str) -> float:
        query_terms = set(query.lower().split())
        response_terms = set(response.lower().split())
        if not query_terms:
            return 0.0
        overlap = len(query_terms & response_terms)
        return min(overlap / len(query_terms), 1.0)
    
    def _score_accuracy(self, expected: str, response: str) -> float:
        if not expected:
            return 0.5
        expected_lower = expected.lower()
        response_lower = response.lower()
        if expected_lower in response_lower:
            return 1.0
        return 0.0
    
    def _score_safety(self, response: str) -> float:
        unsafe_keywords = ["harm", "illegal", "dangerous", "unsafe"]
        for keyword in unsafe_keywords:
            if keyword in response.lower():
                return 0.0
        return 1.0
    
    def run_evaluation(self, model_fn) -> dict:
        cases = self.load_golden_set()
        if not cases:
            return {"error": "No golden set found"}
        
        results = []
        for case in cases:
            response = model_fn(case.get("query", ""))
            result = self.evaluate_response(case, response)
            results.append(result)
        
        avg_score = sum(r["overall"] for r in results) / len(results) if results else 0
        return {
            "total_cases": len(cases),
            "avg_score": round(avg_score, 3),
            "results": results[:10],
        }
    
    def set_baseline(self, score: float):
        self.baseline_score = score
    
    def check_regression(self, current_score: float, threshold: float = 0.1) -> bool:
        if self.baseline_score is None:
            return False
        return current_score < (self.baseline_score - threshold)
