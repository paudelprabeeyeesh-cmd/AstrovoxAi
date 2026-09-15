#!/usr/bin/env python3
"""
Run model evaluation against a golden dataset and track quality metrics.
"""
import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.llm import LLMClient
from app.rag_eval import compute_faithfulness, create_evaluation


def load_golden_dataset(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_benchmark(golden_dataset: list[dict], model: str | None = None) -> dict:
    llm = LLMClient()
    results = []
    for item in golden_dataset:
        query = item["query"]
        expected = item.get("expected", "")
        golden_docs = item.get("golden_doc_ids", [])
        try:
            response = llm.call_llm(query, timeout=30)
            answer = response.get("text", "")
            pred_model = response.get("model", model or "unknown")
            faithfulness = compute_faithfulness(answer, item.get("contexts", [expected]))
            retrieved_ids = item.get("retrieved_ids", [])
            eval_row = create_evaluation(
                query=query,
                retrieved_ids=retrieved_ids,
                golden_ids=golden_docs,
                faithfulness_score=faithfulness,
                metadata={"benchmark": "golden", "model": pred_model},
            )
            results.append(
                {
                    "query": query,
                    "model": pred_model,
                    "faithfulness": faithfulness,
                    "recall_at_5": eval_row["recall_at_5"],
                }
            )
        except Exception as e:
            results.append({"query": query, "error": str(e)})
    return _summarize(results)


def _summarize(results: list[dict]) -> dict:
    valid = [r for r in results if "error" not in r]
    if not valid:
        return {"total": len(results), "errors": len(results)}
    avg_faith = sum(r["faithfulness"] for r in valid) / len(valid)
    avg_recall = sum(r["recall_at_5"] for r in valid) / len(valid)
    return {
        "total": len(results),
        "errors": len(results) - len(valid),
        "avg_faithfulness": round(avg_faith, 4),
        "avg_recall_at_5": round(avg_recall, 4),
        "results": valid,
    }


def main():
    parser = argparse.ArgumentParser(description="Run model evaluation")
    parser.add_argument("--dataset", required=True, help="Path to golden dataset JSON")
    parser.add_argument("--model", default=None, help="Model override")
    args = parser.parse_args()

    dataset = load_golden_dataset(args.dataset)
    print(f"Loaded {len(dataset)} golden examples")
    summary = run_benchmark(dataset, model=args.model)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
