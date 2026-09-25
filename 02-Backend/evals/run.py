
#!/usr/bin/env python3
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.router import call_llm
GOLDEN_PATH = os.path.join(os.path.dirname(__file__), "golden.jsonl")
BASELINE_PATH = os.path.join(os.path.dirname(__file__), "baseline.json")
def load_golden_set():
    if not os.path.exists(GOLDEN_PATH): return []
    with open(GOLDEN_PATH, "r", encoding="utf-8") as f: return [json.loads(l) for l in f if l.strip()]
def score_response(prompt, expected, actual):
    ew = set(expected.lower().split()); aw = set(actual.lower().split())
    if not ew: precision = recall = 1.0 if not aw else 0.0
    else:
        overlap = ew & aw
        precision = len(overlap)/len(aw) if aw else 0.0
        recall = len(overlap)/len(ew)
    faithfulness = 0.5 if any(c in actual.lower() for c in ["i cannot", "i don't know", "unclear"]) else 1.0
    answer_relevance = 1.0 if len(actual) > 50 and precision > 0.3 else 0.0
    return {"precision": round(precision,3), "recall": round(recall,3), "faithfulness": round(faithfulness,3), "answer_relevance": round(answer_relevance,3)}
def load_baseline():
    if not os.path.exists(BASELINE_PATH): return None
    with open(BASELINE_PATH, "r") as f: return json.load(f)
def save_baseline(scores):
    with open(BASELINE_PATH, "w") as f: json.dump(scores, f, indent=2)
def run_evaluation():
    print("=== AstrovoxAI Evaluation Pipeline ===")
    golden_set = load_golden_set()
    if not golden_set: return
    results = []; total = {"precision":0,"recall":0,"faithfulness":0,"answer_relevance":0}
    for i, item in enumerate(golden_set):
        try: actual = call_llm(item["prompt"]).get("text","")
        except Exception as e: actual = ""
        scores = score_response(item["prompt"], item["expected"], actual)
        results.append({"scores": scores})
        for k in total: total[k] += scores[k]
        status = "PASS" if scores["answer_relevance"] >= 0.5 else "FAIL"
        print(f"[{i+1}] {status} - relevance={scores['answer_relevance']:.2f}")
    n = len(results) or 1
    avg = {k: round(total[k]/n,3) for k in total}
    passed = sum(1 for r in results if r["scores"]["answer_relevance"] >= 0.5)
    print(f"Pass rate: {passed}/{len(results)} ({100*passed/len(results):.1f}%)")
    baseline = load_baseline()
    if baseline:
        drop = (baseline["answer_relevance"]-avg["answer_relevance"])/baseline["answer_relevance"] if baseline["answer_relevance"] else 0
        if drop > 0.10:
            print(f"BLOCKED: dropped {100*drop:.1f}%"); sys.exit(1)
    else:
        save_baseline(avg); print("Baseline saved")
if __name__ == "__main__": run_evaluation()
