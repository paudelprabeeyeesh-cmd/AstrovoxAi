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


def load_golden_set():
    """Load golden test pairs."""
    if not os.path.exists(GOLDEN_PATH):
        print(f"Golden set not found at {GOLDEN_PATH}")
        return []
    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def score_response(prompt: str, expected: str, actual: str) -> dict:
    """
    Score a response against expected output.
    Returns precision, recall, faithfulness, answer_relevance.
    """
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


def run_evaluation():
    """Run full evaluation pipeline."""
    print("=== AstrovoxAI Evaluation Pipeline ===")
    
    golden_set = load_golden_set()
    if not golden_set:
        print("No golden test set found. Creating sample...")
        golden_set = [
            {"prompt": "What is the capital of France?", "expected": "Paris"},
            {"prompt": "Explain Newton's first law", "expected": "An object at rest stays at rest"},
        ]
    
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
    print(f"\n=== Summary ===")
    print(f"Tests run: {len(results)}")
    print(f"Avg precision: {total['precision']/n:.3f}")
    print(f"Avg recall: {total['recall']/n:.3f}")
    print(f"Avg faithfulness: {total['faithfulness']/n:.3f}")
    print(f"Avg answer_relevance: {total['answer_relevance']/n:.3f}")
    
    passed = sum(1 for r in results if r["scores"]["answer_relevance"] >= 0.5)
    print(f"Pass rate: {passed}/{len(results)} ({100*passed/len(results):.1f}%)")
    
    return results


if __name__ == "__main__":
    run_evaluation()