#!/usr/bin/env python3
"""
Evaluation pipeline for AstrovoxAI.
Runs golden test set and scores precision/recall/faithfulness/answer_relevance.
"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.router import call_llm
from app.database import get_db

GOLDEN_PATH = os.path.join(os.path.dirname(__file__), "golden.jsonl")
BASELINE_PATH = os.path.join(os.path.dirname(__file__), "baseline.json")


def load_golden_set():
    if not os.path.exists(GOLDEN_PATH):
        print(f"Golden set not found at {GOLDEN_PATH}")
        return []
    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def score_response(prompt: str, expected: str, actual: str) -> dict:
    expected_words = set(expected.lower().split())
    actual_words = set(actual.lower().split())
    
    if not expected_words:
        precision = 1.0 if not actual_words else 0.0
        recall = 1.0 if not actual_words else 0.0
    else:
        overlap = expected_words & actual_words
        precision = len(overlap) / len(actual_words) if actual_words else 0.0
        recall = len(overlap) / len(expected_words)
    
    faithfulness = 1.0 if not any(claim in actual.lower() for claim in ["i cannot", "i don't know", "unclear"]) else 0.5
    answer_relevance = 1.0 if len(actual) > 50 and precision > 0.3 else 0.0
    
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "faithfulness": round(faithfulness, 3),
        "answer_relevance": round(answer_relevance, 3),
    }


def load_baseline() -> dict | None:
    if not os.path.exists(BASELINE_PATH):
        return None
    with open(BASELINE_PATH, "r") as f:
        return json.load(f)


def save_baseline(scores: dict):
    with open(BASELINE_PATH, "w") as f:
        json.dump(scores, f, indent=2)


def run_evaluation():
    print("=== AstrovoxAI Evaluation Pipeline ===")
    
    golden_set = load_golden_set()
    if not golden_set:
        print("No golden test set found.")
        return
    
    print(f"Running {len(golden_set)} test cases...\n")
    
    results = []
    total = {"precision": 0, "recall": 0, "faithfulness": 0, "answer_relevance": 0}
    
    for i, item in enumerate(golden_set):
        prompt = item["prompt"]
        expected = item["expected"]
        
        try:
            llm_result = call_llm(prompt)
            actual = llm_result.get("text", "")
        except Exception as e:
            print(f"[{i+1}] FAILED: {e}")
            actual = ""
        
        scores = score_response(prompt, expected, actual)
        results.append({
            "prompt": prompt,
            "expected": expected,
            "actual": actual[:200],
            "scores": scores,
        })
        
        for k in total:
            total[k] += scores[k]
        
        status = "PASS" if scores["answer_relevance"] >= 0.5 else "FAIL"
        print(f"[{i+1}] {status} - relevance={scores['answer_relevance']:.2f}, precision={scores['precision']:.2f}")
    
    n = len(results) if results else 1
    avg_scores = {
        "precision": round(total["precision"] / n, 3),
        "recall": round(total["recall"] / n, 3),
        "faithfulness": round(total["faithfulness"] / n, 3),
        "answer_relevance": round(total["answer_relevance"] / n, 3),
    }
    
    print(f"\n=== Summary ===")
    print(f"Tests run: {len(results)}")
    for k, v in avg_scores.items():
        print(f"Avg {k}: {v:.3f}")
    
    passed = sum(1 for r in results if r["scores"]["answer_relevance"] >= 0.5)
    pass_rate = 100 * passed / len(results) if results else 0
    print(f"Pass rate: {passed}/{len(results)} ({pass_rate:.1f}%)")
    
    baseline = load_baseline()
    if baseline:
        drop = (baseline["answer_relevance"] - avg_scores["answer_relevance"]) / baseline["answer_relevance"] if baseline["answer_relevance"] else 0
        if drop > 0.10:
            print(f"BLOCKED: answer_relevance dropped {100*drop:.1f}% from baseline {baseline['answer_relevance']}")
            sys.exit(1)
        else:
            print(f"OK: answer_relevance within tolerance")
    else:
        save_baseline(avg_scores)
        print("Baseline saved")
    
    return results


if __name__ == "__main__":
    run_evaluation()
