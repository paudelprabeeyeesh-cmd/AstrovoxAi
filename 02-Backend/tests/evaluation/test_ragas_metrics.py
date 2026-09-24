from evaluation.ragas_metrics import precision_at_k, recall_at_k, faithfulness_score, answer_relevance, context_relevance, RAGASMetrics


def test_precision_at_k_basic():
    retrieved = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    relevant = ["a", "c"]
    assert precision_at_k(retrieved, relevant, k=2) == 0.5


def test_precision_at_k_no_relevant():
    retrieved = [{"id": "a"}, {"id": "b"}]
    relevant = ["c"]
    assert precision_at_k(retrieved, relevant, k=2) == 0.0


def test_precision_at_k_empty_retrieved():
    assert precision_at_k([], ["a"], k=5) == 0.0


def test_precision_at_k_k_greater_than_retrieved():
    retrieved = [{"id": "a"}]
    relevant = ["a"]
    assert precision_at_k(retrieved, relevant, k=5) == 1.0


def test_recall_at_k_basic():
    retrieved = [{"id": "a"}, {"id": "b"}]
    relevant = ["a", "b", "c"]
    assert recall_at_k(retrieved, relevant, k=2) == 2 / 3


def test_recall_at_k_no_relevant_ids():
    assert recall_at_k([{"id": "a"}], [], k=5) == 0.0


def test_faithfulness_score_no_claims():
    answer = "Yes."
    contexts = ["Some context."]
    assert faithfulness_score(answer, contexts) == 1.0


def test_faithfulness_score_supported_claim():
    answer = "The sky is blue."
    contexts = ["The sky is blue."]
    assert faithfulness_score(answer, contexts) == 1.0


def test_faithfulness_score_unsupported_claim():
    answer = "The sky is green."
    contexts = ["The sky is blue."]
    assert faithfulness_score(answer, contexts) == 0.0


def test_answer_relevance_basic():
    query = "What is AI?"
    answer = "AI is artificial intelligence."
    score = answer_relevance(query, answer)
    assert 0.0 <= score <= 1.0


def test_answer_relevance_empty_query():
    assert answer_relevance("", "some answer") == 0.0


def test_context_relevance_basic():
    query = "What is AI?"
    contexts = ["AI is artificial intelligence.", "Machine learning is a subset."]
    score = context_relevance(query, contexts)
    assert 0.0 <= score <= 1.0


def test_context_relevance_empty_contexts():
    assert context_relevance("What is AI?", []) == 0.0


def test_ragas_metrics_evaluate_basic():
    metrics = RAGASMetrics()
    retrieved = [{"id": "a"}, {"id": "b"}]
    relevant = ["a", "b"]
    result = metrics.evaluate(query="What is AI?", answer="AI is artificial intelligence.", retrieved=retrieved, relevant_ids=relevant, contexts=["AI is artificial intelligence."], k=2)
    assert "precision@k" in result
    assert "recall@k" in result
    assert "faithfulness" in result
    assert "answer_relevance" in result
    assert "context_relevance" in result


def test_ragas_metrics_aggregate_empty():
    metrics = RAGASMetrics()
    assert metrics.aggregate() == {}


def test_ragas_metrics_aggregate():
    metrics = RAGASMetrics()
    metrics.evaluate(query="What is AI?", answer="AI is artificial intelligence.", retrieved=[{"id": "a"}], relevant_ids=["a"], contexts=["AI is artificial intelligence."], k=1)
    metrics.evaluate(query="What is ML?", answer="ML is machine learning.", retrieved=[{"id": "b"}], relevant_ids=["b"], contexts=["ML is machine learning."], k=1)
    aggregated = metrics.aggregate()
    assert "precision@k" in aggregated
    assert "recall@k" in aggregated


def test_ragas_metrics_reset():
    metrics = RAGASMetrics()
    metrics.evaluate(query="What is AI?", answer="AI is artificial intelligence.", retrieved=[{"id": "a"}], relevant_ids=["a"], contexts=["AI is artificial intelligence."], k=1)
    metrics.reset()
    assert metrics.aggregate() == {}
