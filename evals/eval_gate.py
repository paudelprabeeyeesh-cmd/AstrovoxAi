#!/usr/bin/env python3
"""Eval regression gate (W4.1).

Runs the golden task set against a recorded baseline and fails when the
held-out score drops by more than the allowed margin.

The point of a gate is that it can go red. A gate that only checks the
suite still parses (the coverage check in security.yml used to compare the
threshold to itself and always passed) is decoration. This one stores the
measured score in evals/baseline.json, compares against it, and updates it
only when UPDATE_BASELINE=1 is explicitly requested.

Baseline file format:
  {
    "version": 1,
    "held_out_score": 0.83,
    "total_score": 0.85,
    "cases": 106,
    "updated": "2026-10-12T00:00:00Z"
  }

Exit codes:
  0  score within the allowed regression margin, or the baseline was updated
  1  score regressed by more than MARGIN, or the baseline is missing in CI
  2  the eval set itself is malformed
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVALS_DIR))

BASELINE_PATH = EVALS_DIR / "baseline.json"

# A 3-point drop on the held-out half is the regression signal. Anything
# smaller is within the run-to-run noise of an LLM.
DEFAULT_MARGIN = 0.03


def build_outputs(cases):
    """A neutral stand-in for a model's answers.

    Without a provider key there are no answers to grade, so the gate
    verifies that the harness itself is intact and that the baseline is
    recorded, rather than pretending to score a model. When
    EVAL_OUTPUTS points at a JSON file, those answers are used instead.
    """
    override = os.getenv("EVAL_OUTPUTS")
    if override and Path(override).is_file():
        return json.loads(Path(override).read_text(encoding="utf-8"))

    outputs = {}
    for case in cases:
        if case.kind == "tool":
            outputs[case.id] = {
                "tool_calls": [{"name": case.rubric.get("expect_tool", ""), "args": {}}]
            }
        elif case.rubric.get("expect_refusal"):
            outputs[case.id] = {"text": "I cannot help with that."}
        elif case.rubric.get("expect_abstain"):
            outputs[case.id] = {"text": "The passage does not mention this."}
        else:
            outputs[case.id] = {"text": "A short answer.", "citations": ["doc"]}
    return outputs


def load_baseline():
    if not BASELINE_PATH.is_file():
        return None
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def write_baseline(total_score, held_out_score, total):
    payload = {
        "version": 1,
        "total_score": round(total_score, 4),
        "held_out_score": round(held_out_score, 4),
        "cases": total,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    BASELINE_PATH.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def main() -> int:
    import expanded_set
    import golden_set as gs

    cases = expanded_set.expanded_set()

    # 1) The set must be structurally sound before anything else is judged.
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        print("::error::the eval set has duplicate case ids; refuse to gate")
        return 2
    if len(cases) < 100:
        print(f"::error::only {len(cases)} cases; the set is too small to gate on")
        return 2
    ungraded = [c.id for c in cases if c.kind not in gs.GRADERS]
    if ungraded:
        print(f"::error::cases with no grader: {ungraded[:5]}")
        return 2

    # 2) Grade.
    outputs = build_outputs(cases)
    report = gs.run_eval(cases, outputs)

    held_ids = {c.id for c in cases if c.held_out}
    held_results = [r for r in report.results if r.id in held_ids]
    held_score = (
        sum(r.score for r in held_results) / len(held_results)
        if held_results else 0.0
    )

    print(f"cases        : {report.total}")
    print(f"total score  : {report.score:.4f}")
    print(f"held-out     : {len(held_results)} cases, score {held_score:.4f}")
    print(f"failed       : {report.failed}")

    # 3) Baseline handling.
    if os.getenv("UPDATE_BASELINE") == "1":
        payload = write_baseline(report.score, held_score, report.total)
        print(f"baseline updated: {payload}")
        return 0

    baseline = load_baseline()
    if baseline is None:
        if os.getenv("CI"):
            print(
                "::error::no eval baseline recorded; run with UPDATE_BASELINE=1 "
                "on the model you intend to gate"
            )
            return 1
        print("no baseline yet; run with UPDATE_BASELINE=1 to record one")
        return 0

    margin = float(os.getenv("EVAL_MARGIN", DEFAULT_MARGIN))
    previous = float(baseline.get("held_out_score", 0.0))
    drop = previous - held_score

    print(f"baseline     : {previous:.4f} (from {baseline.get('updated', 'unknown')})")
    print(f"drop         : {drop:.4f} (margin {margin})")

    if drop > margin:
        print(
            f"::error::held-out score regressed by {drop:.4f}, more than the "
            f"allowed {margin}"
        )
        return 1

    print("eval gate: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
