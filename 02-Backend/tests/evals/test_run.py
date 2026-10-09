import json
import os
import sys

import pytest
from unittest.mock import patch

from evals.run import (
    score_response,
    load_golden_set,
    load_baseline,
    save_baseline,
    run_evaluation,
)


def test_load_golden_set_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "evals.run.GOLDEN_PATH", str(tmp_path / "missing.jsonl")
    )
    assert load_golden_set() == []


def test_load_golden_set_reads_jsonl(tmp_path, monkeypatch):
    golden_path = tmp_path / "golden.jsonl"
    items = [
        {"prompt": "Q1", "expected": "A1"},
        {"prompt": "Q2", "expected": "A2"},
    ]
    with open(golden_path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item) + "\n")

    monkeypatch.setattr("evals.run.GOLDEN_PATH", str(golden_path))
    result = load_golden_set()
    assert len(result) == 2
    assert result[0]["prompt"] == "Q1"
    assert result[1]["expected"] == "A2"


def test_load_golden_set_skips_blank_lines(tmp_path, monkeypatch):
    golden_path = tmp_path / "golden.jsonl"
    with open(golden_path, "w", encoding="utf-8") as f:
        f.write("\n")
        f.write("  \n")
        f.write(json.dumps({"prompt": "Q", "expected": "A"}) + "\n")

    monkeypatch.setattr("evals.run.GOLDEN_PATH", str(golden_path))
    assert len(load_golden_set()) == 1


def test_score_response_basic():
    scores = score_response("What is 2+2?", "four", "four")
    assert scores["precision"] == 1.0
    assert scores["recall"] == 1.0
    assert scores["faithfulness"] == 1.0
    assert scores["answer_relevance"] == 0.0


def test_score_response_empty_expected():
    scores = score_response("prompt", "", "answer")
    assert scores["precision"] == 0.0
    assert scores["recall"] == 0.0


def test_score_response_empty_expected_and_actual():
    scores = score_response("prompt", "", "")
    assert scores["precision"] == 1.0
    assert scores["recall"] == 1.0


def test_score_response_empty_actual():
    scores = score_response("prompt", "expected", "")
    assert scores["precision"] == 0.0
    assert scores["recall"] == 0.0


def test_score_response_faithfulness_detected():
    scores = score_response("prompt", "expected", "I cannot answer this")
    assert scores["faithfulness"] == 0.5


def test_score_response_faithfulness_clean():
    scores = score_response("prompt", "expected", "Here is a good answer.")
    assert scores["faithfulness"] == 1.0


def test_score_response_answer_relevance_long_and_overlap():
    long_answer = " ".join(["word"] * 60)
    scores = score_response("prompt", "word", long_answer)
    assert scores["answer_relevance"] == 1.0


def test_score_response_answer_relevance_short():
    scores = score_response("prompt", "expected", "short")
    assert scores["answer_relevance"] == 0.0


def test_score_response_answer_relevance_low_precision():
    scores = score_response("prompt", "expected", "totally different words here")
    assert scores["answer_relevance"] == 0.0


def test_load_baseline_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "evals.run.BASELINE_PATH", str(tmp_path / "missing.json")
    )
    assert load_baseline() is None


def test_load_baseline_reads_json(tmp_path, monkeypatch):
    baseline_path = tmp_path / "baseline.json"
    data = {"answer_relevance": 0.8, "precision": 0.9}
    with open(baseline_path, "w") as f:
        json.dump(data, f)

    monkeypatch.setattr("evals.run.BASELINE_PATH", str(baseline_path))
    assert load_baseline() == data


def test_save_baseline_writes_json(tmp_path, monkeypatch):
    baseline_path = tmp_path / "baseline.json"
    monkeypatch.setattr("evals.run.BASELINE_PATH", str(baseline_path))
    scores = {"precision": 0.9, "recall": 0.8}
    save_baseline(scores)
    with open(baseline_path) as f:
        loaded = json.load(f)
    assert loaded == scores


def test_run_evaluation_no_golden_set(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("evals.run.GOLDEN_PATH", str(tmp_path / "nonexistent.jsonl"))
    run_evaluation()
    captured = capsys.readouterr()
    assert "AstrovoxAI Evaluation Pipeline" in captured.out


def test_run_evaluation_with_mocked_llm(tmp_path, monkeypatch, capsys):
    golden_path = tmp_path / "golden.jsonl"
    items = [
        {"prompt": "Q1", "expected": "hello world"},
        {"prompt": "Q2", "expected": "foo bar baz"},
    ]
    with open(golden_path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item) + "\n")

    monkeypatch.setattr("evals.run.GOLDEN_PATH", str(golden_path))
    monkeypatch.setattr(
        "evals.run.BASELINE_PATH", str(tmp_path / "baseline.json")
    )

    with patch("evals.run.call_llm", return_value={"text": "hello world foo bar baz extra padding words"}):
        run_evaluation()

    captured = capsys.readouterr()
    assert "Pass rate:" in captured.out
