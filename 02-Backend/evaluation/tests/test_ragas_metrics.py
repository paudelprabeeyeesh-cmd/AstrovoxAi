from evaluation.ragas_metrics import (
    precision_at_k,
    recall_at_k,
    faithfulness_score,
    answer_relevance,
    context_relevance,
    RAGASMetrics,
)


def test_precision_at_k_hits():
    retrieved = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    relevant_ids = ["a", "c"]
    assert precision_at_k(retrieved, relevant_ids, k=2) == 0.5
    assert precision_at_k(retrieved, relevant_ids, k=3) == 2 / 3


def test_precision_at_k_empty():
    assert precision_at_k([], ["a"], k=5) == 0.0


def test_recall_at_k_basic():
    retrieved = [{"id": "a"}, {"id": "b"}]
    relevant_ids = ["a", "c"]
    assert recall_at_k(retrieved, relevant_ids, k=2) == 1 / 2


def test_recall_at_k_no_relevant():
    assert recall_at_k([{"id": "a"}], [], k=5) == 0.0


def test_faithfulness_score():
    answer = "Paris is the capital of France. It is a beautiful city."
    contexts = ["Paris is the capital of France."]
    score = faithfulness_score(answer, contexts)
    assert 0.0 <= score <= 1.0


def test_answer_relevance_basic():
    query = "what is the capital of France"
    answer = "The capital of France is Paris."
    score = answer_relevance(query, answer)
    assert score > 0.0


def test_context_relevance_basic():
    query = "capital of France"
    contexts = ["Paris is the capital of France."]
    score = context_relevance(query, contexts)
    assert score > 0.0


def test_context_relevance_empty():
    assert context_relevance("query", []) == 0.0


def test_ragas_metrics_evaluate():
    metrics = RAGASMetrics()
    retrieved = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    relevant_ids = ["a", "c"]
    result = metrics.evaluate(
        query="capital of France",
        answer="Paris is the capital of France.",
        retrieved=retrieved,
        relevant_ids=relevant_ids,
        contexts=["Paris is the capital of France."],
        k=3,
    )
    assert "precision@k" in result
    assert "recall@k" in result
    assert "faithfulness" in result
    assert "answer_relevance" in result
    assert "context_relevance" in result


def test_ragas_metrics_aggregate():
    metrics = RAGASMetrics()
    metrics.evaluate("q", "a", [{"id": "a"}], ["a"], ["ctx"], k=1)
    metrics.evaluate("q", "a", [{"id": "a"}], ["a"], ["ctx"], k=1)
    agg = metrics.aggregate()
    assert agg


def test_ragas_metrics_reset():
    metrics = RAGASMetrics()
    metrics.evaluate("q", "a", [{"id": "a"}], ["a"], ["ctx"], k=1)
    metrics.reset()
    assert metrics.aggregate() == {}
