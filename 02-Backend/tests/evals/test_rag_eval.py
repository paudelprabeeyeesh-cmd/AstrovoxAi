import sys
import pytest
from unittest.mock import MagicMock, patch

# Save any existing evals.run module (e.g., a mock from another test file)
_original_run = sys.modules.pop("evals.run", None)

_mock_run = MagicMock()
_mock_run.GoldenSetEvaluator = MagicMock
sys.modules["evals.run"] = _mock_run

try:
    from evals.rag_eval import RAGEvaluator  # noqa: E402
finally:
    if _original_run is not None:
        sys.modules["evals.run"] = _original_run
    else:
        sys.modules.pop("evals.run", None)


@pytest.fixture
def evaluator():
    return RAGEvaluator()


def test_precision_at_k_basic(evaluator):
    retrieved = [
        {"id": "a"},
        {"id": "b"},
        {"id": "c"},
    ]
    relevant_ids = ["a", "b"]
    assert evaluator.precision_at_k(retrieved, relevant_ids, k=2) == 1.0


def test_precision_at_k_partial(evaluator):
    retrieved = [
        {"id": "a"},
        {"id": "b"},
        {"id": "c"},
    ]
    relevant_ids = ["a", "c"]
    assert evaluator.precision_at_k(retrieved, relevant_ids, k=2) == 0.5


def test_precision_at_k_no_relevant(evaluator):
    retrieved = [
        {"id": "a"},
        {"id": "b"},
    ]
    relevant_ids = ["c", "d"]
    assert evaluator.precision_at_k(retrieved, relevant_ids, k=2) == 0.0


def test_precision_at_k_empty_inputs(evaluator):
    assert evaluator.precision_at_k([], ["a"], k=5) == 0.0
    assert evaluator.precision_at_k([{"id": "a"}], [], k=5) == 0.0


def test_recall_at_k_basic(evaluator):
    retrieved = [
        {"id": "a"},
        {"id": "b"},
    ]
    relevant_ids = ["a", "b", "c"]
    assert evaluator.recall_at_k(retrieved, relevant_ids, k=2) == pytest.approx(2 / 3)


def test_recall_at_k_all_relevant(evaluator):
    retrieved = [
        {"id": "a"},
        {"id": "b"},
    ]
    relevant_ids = ["a", "b"]
    assert evaluator.recall_at_k(retrieved, relevant_ids, k=2) == 1.0


def test_recall_at_k_empty_relevant(evaluator):
    retrieved = [{"id": "a"}]
    assert evaluator.recall_at_k(retrieved, [], k=5) == 0.0


def test_answer_relevance_overlap(evaluator):
    query = "what is the capital of france"
    answer = "The capital of France is Paris."
    score = evaluator.answer_relevance(query, answer)
    assert 0.0 < score <= 1.0


def test_answer_relevance_no_overlap(evaluator):
    query = "hello world"
    answer = "goodbye universe"
    assert evaluator.answer_relevance(query, answer) == 0.0


def test_answer_relevance_empty_query(evaluator):
    assert evaluator.answer_relevance("", "some answer") == 0.0


def test_evaluate_query_returns_metrics(evaluator):
    result = evaluator.evaluate_query(
        query="capital of France",
        retrieved=[{"id": "a"}, {"id": "b"}],
        answer="The capital of France is Paris.",
        relevant_ids=["a", "c"],
    )
    assert "query" in result
    assert "precision@5" in result
    assert "recall@5" in result
    assert "answer_relevance" in result
    assert result["query"] == "capital of France"
    assert 0.0 <= result["precision@5"] <= 1.0
    assert 0.0 <= result["recall@5"] <= 1.0
    assert 0.0 <= result["answer_relevance"] <= 1.0


def test_evaluate_query_precision_calculation(evaluator):
    retrieved = [
        {"id": "1"},
        {"id": "2"},
        {"id": "3"},
    ]
    relevant_ids = ["1", "3"]
    result = evaluator.evaluate_query(
        query="q",
        retrieved=retrieved,
        answer="answer text",
        relevant_ids=relevant_ids,
    )
    assert result["precision@5"] == 0.667
    assert result["recall@5"] == 1.0
