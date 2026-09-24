import numpy as np
from verification_loop.targeted_test_selection import (
    ChangedFile,
    CoverageEntry,
    TargetedTestSelector,
)


def test_select_returns_only_covering_tests():
    selector = TargetedTestSelector(coverage_map={"app/main.py": [1, 2, 3]})
    changed = [ChangedFile(path="app/main.py", added_lines=[2], removed_lines=[], modified_lines=[])]
    selected = selector.select(changed, ["test_a", "test_b"])
    assert all(s.score > 0.0 for s in selected)
    assert len(selected) == 2


def test_selection_scores_reflect_overlap():
    selector = TargetedTestSelector(coverage_map={"app/main.py": [2]})
    changed = [ChangedFile(path="app/main.py", added_lines=[2], removed_lines=[], modified_lines=[])]
    selected = selector.select(changed, ["t1"])
    assert selected[0].score == 1.0


def test_no_selection_when_no_coverage():
    selector = TargetedTestSelector(coverage_map={})
    changed = [ChangedFile(path="app/main.py", added_lines=[1], removed_lines=[], modified_lines=[])]
    selected = selector.select(changed, ["t1", "t2"])
    assert selected == []


def test_selection_coverage_metric():
    selector = TargetedTestSelector(coverage_map={"app/main.py": [1, 2]})
    changed = [ChangedFile(path="app/main.py", added_lines=[1, 2], removed_lines=[], modified_lines=[])]
    selected = selector.select(changed, ["t1"])
    metrics = selector.selection_coverage(selected, changed)
    assert metrics["overall"] == 1.0
    assert metrics["by_file"]["app/main.py"] == 1.0


def test_coverage_map_accumulates():
    selector = TargetedTestSelector()
    selector.record_coverage("t1", "a.py", [1, 2])
    selector.record_coverage("t1", "a.py", [2, 3])
    assert sorted(selector.coverage_map["a.py"]) == [1, 2, 3]


def test_selection_sorted_by_score_descending():
    selector = TargetedTestSelector(coverage_map={
        "app/a.py": [10],
        "app/b.py": [20],
    })
    changed = [
        ChangedFile(path="app/a.py", added_lines=[10], removed_lines=[], modified_lines=[]),
        ChangedFile(path="app/b.py", added_lines=[20], removed_lines=[], modified_lines=[]),
    ]
    selected = selector.select(changed, ["t1", "t2"])
    scores = np.array([s.score for s in selected])
    assert np.all(scores[:-1] >= scores[1:])
