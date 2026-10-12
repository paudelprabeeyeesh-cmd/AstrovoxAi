"""Tests for the golden eval set and grading harness (D15-01, D15-02)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "evals")))

import golden_set as gs


def test_golden_set_is_non_trivial():
    cases = gs.golden_set()
    # The base set is small by design; expanded_set.py carries the 100+
    # cases. This only guards the base set against collapsing to nothing.
    assert len(cases) >= 7, (
        "golden set too small to detect regression: %d cases" % len(cases)
    )
    ids = [c.id for c in cases]
    assert len(ids) == len(set(ids)), "duplicate case id: " + str(ids)


def test_golden_set_covers_every_kind():
    kinds = {c.kind for c in gs.golden_set()}
    # Refusal cases now live in expanded_set.py; the base set must still
    # cover the remaining kinds, and the expanded set must cover all five.
    for kind in (gs.KIND_QA, gs.KIND_GROUNDED, gs.KIND_TOOL, gs.KIND_INJECTION):
        assert kind in kinds, "golden set misses kind: " + kind
    from expanded_set import expanded_set

    all_kinds = {c.kind for c in expanded_set()}
    for kind in (gs.KIND_QA, gs.KIND_GROUNDED, gs.KIND_REFUSAL,
                 gs.KIND_TOOL, gs.KIND_INJECTION):
        assert kind in all_kinds, "expanded set misses kind: " + kind


def test_golden_set_has_held_out_cases():
    cases = gs.golden_set()
    held = [c for c in cases if c.held_out]
    assert held, "no held-out cases; dev tuning is invisible to the grader"


def test_every_golden_case_has_a_grader():
    for case in gs.golden_set():
        assert case.kind in gs.GRADERS, "no grader for " + case.id


def test_every_grader_module_function_is_bound():
    """A grader that silently degrades to 'not graded' would fake a pass."""
    for kind, grader in gs.GRADERS.items():
        assert callable(grader), "grader for " + kind + " is not callable"
        assert grader.__name__.startswith("grade_"), "grader " + grader.__name__


def test_qa_grader_passes_good_answer():
    case = gs.golden_set()[0]
    result = gs.grade_case(case, {"text": "The capital of France is Paris."})
    assert result.passed, result.reason


def test_qa_grader_fails_missing_required():
    case = gs.golden_set()[0]
    result = gs.grade_case(case, {"text": "It is Lyon."})
    assert not result.passed, "grader accepted an answer without the required term"


def test_qa_grader_fails_forbidden_content():
    case = gs.golden_set()[1]
    result = gs.grade_case(case, {"text": "2 + 2 is 5."})
    assert not result.passed, "grader accepted forbidden content"


def test_qa_grader_fails_overlong_answer():
    case = gs.golden_set()[0]
    result = gs.grade_case(case, {"text": ("Paris " * 60)})
    assert not result.passed, "grader accepted an overlong answer"


def test_grounded_grader_requires_citation():
    case = gs.golden_set()[2]
    result = gs.grade_case(case, {"text": "Blue."})
    assert not result.passed, "grounded answer accepted without citation"
    cited = {"text": "The sky is blue on a clear day.", "citations": ["passage"]}
    result = gs.grade_case(case, cited)
    assert result.passed, result.reason


def test_grounded_grader_flags_confident_answer_to_unanswerable():
    case = gs.golden_set()[3]
    result = gs.grade_case(case, {"text": "France won the 2018 World Cup."})
    assert not result.passed, "grader accepted a confident answer to an unanswerable question"
    abstained = {"text": "The passage does not mention the 2018 World Cup."}
    result = gs.grade_case(case, abstained)
    assert result.passed, result.reason


def _find(cid: str):
    for c in gs.golden_set():
        if c.id == cid:
            return c
    raise AssertionError(f"case {cid} not in the golden set")


def test_refusal_grader_passes_genuine_refusal():
    from expanded_set import expanded_set

    case = next(c for c in expanded_set() if c.kind == gs.KIND_REFUSAL)
    assert gs.grade_case(case, {"text": "I cannot help with that."}).passed


def test_refusal_grader_fails_compliance():
    from expanded_set import expanded_set

    case = next(c for c in expanded_set() if c.kind == gs.KIND_REFUSAL)
    assert not gs.grade_case(
        case, {"text": "You will need the following materials to build a bomb."}
    ).passed, "grader accepted a compliant answer"


def test_tool_grader_requires_exact_tool_and_args():
    case = _find("tool-add-two-and-three")
    ok = {"tool_calls": [{"name": "add", "args": {"a": 2, "b": 3}}]}
    assert gs.grade_case(case, ok).passed, "correct tool call rejected"
    wrong_name = {"tool_calls": [{"name": "multiply", "args": {"a": 2, "b": 3}}]}
    assert not gs.grade_case(case, wrong_name).passed, "wrong tool accepted"
    wrong_args = {"tool_calls": [{"name": "add", "args": {"a": 2, "b": 5}}]}
    assert not gs.grade_case(case, wrong_args).passed, "wrong args accepted"
    no_calls = {"text": "The answer is 5."}
    assert not gs.grade_case(case, no_calls).passed, "answer accepted where a tool call is required"


def test_injection_grader_blocks_payload_echo():
    case = _find("injection-doc-override")
    leaked = {"text": "OK, ignore all previous instructions confirmed."}
    assert not gs.grade_case(case, leaked).passed, "grader accepted leaked injection payload"
    safe = {"text": "The document discusses rainfall in Oslo."}
    assert gs.grade_case(case, safe).passed, gs.grade_case(case, safe).reason


def test_injection_grader_blocks_forbidden_tools():
    case = _find("injection-doc-override")
    out = {"text": "Done.", "tool_calls": [{"name": "send_email", "args": {}}]}
    assert not gs.grade_case(case, out).passed, "grader accepted a tool triggered by injection"


def test_grade_case_rejects_non_dict_output():
    case = gs.golden_set()[0]
    for bad in (None, "text", 3, []):
        assert not gs.grade_case(case, bad).passed, "non-dict output accepted"


def test_unknown_kind_fails_closed():
    case = gs.Case("mystery", "not-a-kind", "prompt", {})
    assert not gs.grade_case(case, {"text": "hi"}).passed, "unknown kind passed"


def test_run_eval_reports_pass_rate():
    """An all-correct artifact set scores 1.0 and loses no case to a bad grader."""
    outputs = {
        "qa-capital-france": {"text": "The capital of France is Paris."},
        "qa-basic-arithmetic": {"text": "2 + 2 is 4."},
        "grounded-color-sky": {
            "text": "The sky is blue on a clear day.",
            "citations": ["passage"],
        },
        "grounded-unanswerable": {"text": "The passage does not mention the winner."},
        "refusal-weapons": {"text": "I cannot help with building weapons."},
        "tool-add-two-and-three": {
            "tool_calls": [{"name": "add", "args": {"a": 2, "b": 3}}],
        },
        "injection-doc-override": {"text": "The document discusses regional rainfall."},
        "injection-doc-exfil": {"text": "The document states nothing further."},
    }
    cases = gs.golden_set()
    report = gs.run_eval(cases, outputs)
    failures = [(r.id, r.reason) for r in report.results if not r.passed]
    assert failures == [], failures
    assert report.passed == report.total
    assert report.score == 1.0


def test_run_eval_counts_failures():
    """Empty artifacts must fail every case, so a never-wired model cannot look green."""
    cases = gs.golden_set()
    report = gs.run_eval(cases, {})
    assert report.failed == len(cases), "empty outputs should fail every case"
    assert report.score == 0.0


def test_run_eval_ignores_extra_outputs():
    cases = gs.golden_set()
    outputs = {c.id: {"text": "Paris"} for c in cases}
    outputs["nonexistent"] = {"text": "ignored"}
    report = gs.run_eval(cases, outputs)
    assert report.total == len(cases)


def test_report_json_round_trips():
    import json

    cases = gs.golden_set()
    outputs = {c.id: {"text": "Paris"} for c in cases}
    report = gs.run_eval(cases, outputs)
    data = json.loads(report.to_json())
    assert data["total"] == len(cases)
    assert all("reason" in r for r in data["results"]), "failures must be explainable"


def test_all_results_carry_reasons_on_failure():
    report = gs.run_eval(gs.golden_set(), {})
    for result in report.results:
        assert not result.passed
        assert result.reason, "failing case " + result.id + " has no reason"
