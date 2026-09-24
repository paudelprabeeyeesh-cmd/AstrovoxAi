import logging
from typing import Any
import numpy as np

logger = logging.getLogger(__name__)


def precision_at_k(retrieved: list[dict], relevant_ids: list[str], k: int = 5) -> float:
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    relevant_in_top_k = sum(1 for doc in top_k if doc.get("id") in relevant_ids)
    return relevant_in_top_k / min(k, len(top_k))


def recall_at_k(retrieved: list[dict], relevant_ids: list[str], k: int = 5) -> float:
    if not relevant_ids:
        return 0.0
    top_k = retrieved[:k]
    relevant_in_top_k = sum(1 for doc in top_k if doc.get("id") in relevant_ids)
    return relevant_in_top_k / len(relevant_ids)


def faithfulness_score(answer: str, contexts: list[str]) -> float:
    answer_lower = answer.lower()
    claim_markers = ["is", "are", "was", "were", "has", "have", "can", "will", "does", "did"]
    claims = [c.strip() for c in answer_lower.split(".") if any(m in c for m in claim_markers) and len(c.strip()) > 5]
    if not claims:
        return 1.0
    supported = 0
    for claim in claims:
        if any(claim in ctx.lower() or ctx.lower() in claim for ctx in contexts):
            supported += 1
    return supported / len(claims) if claims else 1.0


def answer_relevance(query: str, answer: str) -> float:
    query_terms = set(query.lower().split())
    answer_terms = set(answer.lower().split())
    if not query_terms:
        return 0.0
    overlap = len(query_terms & answer_terms)
    return overlap / len(query_terms)


def context_relevance(query: str, contexts: list[str]) -> float:
    if not contexts:
        return 0.0
    query_terms = set(query.lower().split())
    scores = []
    for ctx in contexts:
        ctx_terms = set(ctx.lower().split())
        overlap = len(query_terms & ctx_terms)
        scores.append(overlap / len(query_terms) if query_terms else 0.0)
    return float(np.mean(scores))


class RAGASMetrics:
    def __init__(self):
        self._history: list[dict[str, Any]] = []

    def evaluate(
        self,
        query: str,
        answer: str,
        retrieved: list[dict],
        relevant_ids: list[str],
        contexts: list[str] | None = None,
        k: int = 5,
    ) -> dict[str, float]:
        contexts = contexts or []
        prec = precision_at_k(retrieved, relevant_ids, k)
        rec = recall_at_k(retrieved, relevant_ids, k)
        faith = faithfulness_score(answer, contexts)
        ans_rel = answer_relevance(query, answer)
        ctx_rel = context_relevance(query, contexts)
        metrics = {
            "precision@k": round(prec, 4),
            "recall@k": round(rec, 4),
            "faithfulness": round(faith, 4),
            "answer_relevance": round(ans_rel, 4),
            "context_relevance": round(ctx_rel, 4),
        }
        self._history.append(metrics)
        return metrics

    def aggregate(self) -> dict[str, float]:
        if not self._history:
            return {}
        keys = self._history[0].keys()
        return {k: round(float(np.mean([m[k] for m in self._history])), 4) for k in keys}

    def reset(self) -> None:
        self._history.clear()
