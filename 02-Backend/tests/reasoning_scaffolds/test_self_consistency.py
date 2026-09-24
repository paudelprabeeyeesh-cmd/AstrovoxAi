from __future__ import annotations

import pytest

from reasoning_scaffolds.self_consistency import majority_vote, self_consistency, ConsistencyResult


def test_majority_vote_basic():
    result = majority_vote(["A", "A", "B"])
    assert result is not None
    answer, confidence = result
    assert answer == "A"
    assert confidence == 2 / 3


def test_majority_vote_empty():
    assert majority_vote([]) is None


def test_majority_vote_tie():
    result = majority_vote(["A", "B"])
    assert result is not None
    assert result[0] in ("A", "B")
    assert result[1] == 0.5


def test_self_consistency_mocked():
    def fake_generate(problem: str) -> str:
        return "final answer: 42"

    def fake_extract(raw: str) -> str:
        return raw.split(":")[-1].strip()

    result = self_consistency("What is 6*7?", fake_generate, fake_extract, num_samples=3)
    assert result is not None
    assert result[0] == "42"


def test_consistency_result_from_samples():
    res = ConsistencyResult.from_samples(["A", "A", "B"])
    assert res.answer == "A"
    assert res.confidence == pytest.approx(2 / 3)
