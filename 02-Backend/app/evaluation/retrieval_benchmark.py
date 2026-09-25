import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    benchmark_name: str
    passed: bool
    score: float
    recall_at_k: dict[int, float] = field(default_factory=dict)
    mrr: float = 0.0
    ndcg: dict[int, float] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)


class RetrievalBenchmark:
    def __init__(self):
        self._results: list[BenchmarkResult] = []

    def run_benchmark(self, queries: list[dict[str, Any]], ground_truth: dict[str, list[str]]) -> BenchmarkResult:
        all_results: list[dict[str, Any]] = []
        ks = [1, 3, 5, 10]
        recall_sums: dict[int, float] = {k: 0.0 for k in ks}
        mrr_sum = 0.0
        ndcg_sums: dict[int, float] = {k: 0.0 for k in ks}

        for query_item in queries:
            qid = query_item.get("id") or query_item.get("query", "")
            query_text = query_item.get("query", str(qid))
            retrieved = query_item.get("results", [])
            relevant = ground_truth.get(qid, [])

            recall_scores = {k: self.calculate_recall_at_k(retrieved, relevant, k) for k in ks}
            mrr = self.calculate_mrr(retrieved, relevant)
            ndcg_scores = {k: self.calculate_ndcg(retrieved, relevant, k) for k in ks}

            for k in ks:
                recall_sums[k] += recall_scores[k]
                ndcg_sums[k] += ndcg_scores[k]
            mrr_sum += mrr

            all_results.append({
                "query": query_text,
                "recall": recall_scores,
                "mrr": mrr,
                "ndcg": ndcg_scores,
            })

        n = max(len(queries), 1)
        avg_recall = {k: recall_sums[k] / n for k in ks}
        avg_mrr = mrr_sum / n
        avg_ndcg = {k: ndcg_sums[k] / n for k in ks}

        passed = avg_recall.get(5, 0.0) >= 0.5
        score = (avg_recall.get(5, 0.0) + avg_mrr + avg_ndcg.get(5, 0.0)) / 3.0

        result = BenchmarkResult(
            benchmark_name="retrieval_benchmark",
            passed=passed,
            score=round(score, 4),
            recall_at_k={k: round(v, 4) for k, v in avg_recall.items()},
            mrr=round(avg_mrr, 4),
            ndcg={k: round(v, 4) for k, v in avg_ndcg.items()},
            details={"queries_evaluated": n, "per_query": all_results},
        )
        self._results.append(result)
        return result

    def calculate_recall_at_k(self, results: list[dict[str, Any]], relevant_ids: list[str], k: int = 5) -> float:
        if not relevant_ids:
            return 0.0
        top_k = results[:k]
        relevant_in_top_k = sum(1 for doc in top_k if doc.get("id") in relevant_ids)
        return relevant_in_top_k / len(relevant_ids)

    def calculate_mrr(self, results: list[dict[str, Any]], relevant_ids: list[str]) -> float:
        if not relevant_ids:
            return 0.0
        for idx, doc in enumerate(results):
            if doc.get("id") in relevant_ids:
                return 1.0 / (idx + 1)
        return 0.0

    def calculate_ndcg(self, results: list[dict[str, Any]], relevant_ids: list[str], k: int = 5) -> float:
        if not relevant_ids:
            return 0.0
        top_k = results[:k]
        dcg = sum(
            (1.0 / (idx + 1)) if doc.get("id") in relevant_ids else 0.0
            for idx, doc in enumerate(top_k)
        )
        ideal_order = sorted([1 if doc.get("id") in relevant_ids else 0 for doc in top_k], reverse=True)
        idcg = sum(score / (idx + 1) for idx, score in enumerate(ideal_order))
        return dcg / idcg if idcg > 0 else 0.0

    def generate_report(self) -> dict[str, Any]:
        if not self._results:
            return {"error": "No benchmarks run"}
        latest = self._results[-1]
        return {
            "benchmark_name": latest.benchmark_name,
            "passed": latest.passed,
            "score": latest.score,
            "recall_at_k": latest.recall_at_k,
            "mrr": latest.mrr,
            "ndcg": latest.ndcg,
            "total_runs": len(self._results),
        }
