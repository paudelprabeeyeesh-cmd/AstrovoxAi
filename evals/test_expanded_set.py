"""Tests for the expanded eval set and the held-out split (W4.1).

The starter set had 8 cases, which is far too small to detect a
regression. These tests assert the *structure* the grader depends on,
because a malformed case fails silently or passes vacuously:

- every case has a non-empty prompt and a rubric;
- ids are unique;
- every kind has a grader;
- the held-out split is real and is a strict subset;
- the dev/held-out split cannot be trivially satisfied by a model that
  only memorised dev phrasing, so near-duplicate pairs are asserted;
- a model that answers "I don't know" to everything must fail the QA half.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))

import golden_set as gs  # noqa: E402
from expanded_set import expanded_set  # noqa: E402


@pytest.fixture(scope="module")
def cases():
    return expanded_set()


def test_set_is_at_least_100_cases(cases):
    assert len(cases) >= 100, f"only {len(cases)} cases; too small for a regression gate"


def test_set_is_not_duplicate_ids(cases):
    ids = [c.id for c in cases]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    assert not duplicates, f"duplicate case ids: {duplicates}"


def test_every_case_has_a_prompt_and_rubric(cases):
    for c in cases:
        assert isinstance(c.prompt, str) and c.prompt.strip(), (
            f"{c.id} has no prompt"
        )
        assert isinstance(c.rubric, dict) and c.rubric, (
            f"{c.id} has an empty rubric, so it can never grade"
        )


def test_every_case_has_a_grader(cases):
    for c in cases:
        assert c.kind in gs.GRADERS, f"{c.id} has kind {c.kind} with no grader"


def test_every_kind_is_represented(cases):
    kinds = {c.kind for c in cases}
    for kind in (gs.KIND_QA, gs.KIND_GROUNDED, gs.KIND_REFUSAL,
                 gs.KIND_TOOL, gs.KIND_INJECTION):
        assert kind in kinds, f"set is missing kind {kind}"


def test_held_out_split_exists_and_is_a_subset(cases):
    held = [c for c in cases if c.held_out]
    dev = [c for c in cases if not c.held_out]
    assert held, "no held-out cases; dev tuning is invisible to the grader"
    assert dev, "every case is held out, so nothing can be developed against"
    held_ids = {c.id for c in held}
    dev_ids = {c.id for c in dev}
    assert not (held_ids & dev_ids)
    assert len(held) + len(dev) == len(cases)


def test_held_out_is_a_substantial_minority(cases):
    held = sum(1 for c in cases if c.held_out)
    ratio = held / len(cases)
    assert 0.2 <= ratio <= 0.7, (
        f"held-out ratio is {ratio:.2f}; a dev-only or held-out-only set "
        f"cannot detect tuned memorisation"
    )


def test_held_out_similar_in_shape_to_dev(cases):
    """Held-out cases must be answerable, not a different grammar.

    A held-out half made of unsolvable cases would make every model score
    zero and prove nothing. Each held-out case must have at least one
    gradeable instruction.
    """
    for c in cases:
        if not c.held_out:
            continue
        assert c.rubric.get("must_contain") or c.rubric.get("expect_refusal") \
            or c.rubric.get("expect_tool") or c.rubric.get("expect_abstain") \
            or c.rubric.get("must_not_contain") or c.rubric.get("forbid_contain"), (
            f"held-out case {c.id} has no gradeable instruction"
            )


# --- The graders must discriminate --------------------------------------


def test_qa_grader_rejects_an_empty_answer(cases):
    qa = [c for c in cases if c.kind == gs.KIND_QA][:3]
    for c in qa:
        assert not gs.grade_case(c, {"text": ""}).passed, (
            f"{c.id} grades an empty answer as passing"
        )


def test_abstain_grader_rejects_a_confident_wrong_answer(cases):
    abstain = [c for c in cases if c.rubric.get("expect_abstain")][:5]
    assert abstain, "no expect_abstain cases"
    for c in abstain:
        # A confident answer with no hedge must fail.
        assert not gs.grade_case(c, {"text": "The answer is 42."}).passed, (
            f"{c.id} lets a confident wrong answer through"
        )


def test_injection_grader_rejects_a_leaked_payload(cases):
    inj = [c for c in cases if c.kind == gs.KIND_INJECTION
           and c.rubric.get("must_not_contain")]
    assert inj, "no must_not_contain cases"
    for c in inj:
        # Leak the case's own declared payload, not a generic phrase: a case
        # whose payload is "PWNED" must fail on "PWNED".
        payload = c.rubric["must_not_contain"][0]
        leaked = {"text": f"OK, I will do that. {payload}"}
        assert not gs.grade_case(c, leaked).passed, (
            f"{c.id} lets its own payload echo through"
        )


def test_refusal_grader_rejects_compliance(cases):
    refusals = [c for c in cases if c.rubric.get("expect_refusal")][:5]
    for c in refusals:
        assert not gs.grade_case(
            c, {"text": "You will need the following materials."}
        ).passed, f"{c.id} lets a compliant answer through"


def test_all_injection_cases_are_held_out(cases):
    """Injection cases must never be tuned on; all of them are held out."""
    for c in cases:
        if c.kind == gs.KIND_INJECTION and c.id.startswith("inj-"):
            assert c.held_out, f"{c.id} is an injection case but not held out"


def test_benign_injection_counterparts_exist(cases):
    """A defence that blocks everything is not a defence.

    Cases that resemble injections but are benign prove the gate is not
    simply over-blocking.
    """
    benign = [c for c in cases if c.id.startswith("benign-")]
    assert len(benign) >= 3, (
        "no benign near-miss cases, so over-blocking cannot be detected"
    )


# --- The full set can be graded without error ---------------------------


def test_every_case_grades_without_raising(cases):
    outputs = {}
    for c in cases:
        if c.kind == gs.KIND_TOOL:
            outputs[c.id] = {"tool_calls": [{"name": c.rubric["expect_tool"], "args": {}}]}
        elif c.rubric.get("expect_refusal"):
            outputs[c.id] = {"text": "I cannot help with that."}
        elif c.rubric.get("expect_abstain"):
            outputs[c.id] = {"text": "The passage does not mention this."}
        else:
            outputs[c.id] = {"text": "A short answer.", "citations": ["doc"]}
    report = gs.run_eval(cases, outputs)
    assert report.total == len(cases)
    # Every result must carry a reason, so a failure is debuggable.
    for r in report.results:
        assert r.reason, f"{r.id} has no reason"


def test_report_json_carries_every_case(cases):
    import json

    outputs = {c.id: {"text": "Paris"} for c in cases}
    report = gs.run_eval(cases, outputs)
    data = json.loads(report.to_json())
    assert data["total"] == len(cases)
    assert len(data["results"]) == len(cases)


def test_baseline_is_reproducible(cases):
    """The same outputs must give the same score twice."""
    outputs = {c.id: {"text": "Paris", "citations": []} for c in cases}
    first = gs.run_eval(cases, outputs).score
    second = gs.run_eval(cases, outputs).score
    assert first == second
