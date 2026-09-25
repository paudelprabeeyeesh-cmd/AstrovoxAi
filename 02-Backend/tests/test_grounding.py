import pytest
from app.core.grounding import score_confidence, has_supporting_context, ground_answer, should_refuse


def test_score_confidence_no_contexts():
    assert score_confidence("answer", [], "query") == 0.0


def test_score_confidence_low_score():
    contexts = [{"content": "something", "score": 0.5}]
    assert score_confidence("answer", contexts, "query") < 0.7


def test_has_supporting_context_true():
    contexts = [{"content": "python is a programming language used for web development", "score": 0.9}]
    assert has_supporting_context("python is used for web development", contexts) is True


def test_has_supporting_context_false():
    contexts = [{"content": "completely unrelated content about cooking recipes", "score": 0.9}]
    assert has_supporting_context("python programming", contexts) is False


def test_ground_answer_no_context():
    answer, refused, confidence = ground_answer("some answer", [], "query")
    assert refused is True
    assert "I don't know" in answer


def test_ground_answer_low_confidence():
    contexts = [{"content": "some context", "score": 0.6, "id": "ctx1"}]
    answer, refused, confidence = ground_answer("some answer", contexts, "query")
    assert refused is True
    assert "I don't know" in answer


def test_ground_answer_high_confidence():
    contexts = [{"content": "python is a programming language used for web development and data science", "score": 0.9, "id": "ctx1"}]
    answer, refused, confidence = ground_answer("python is used for web development", contexts, "python web")
    assert refused is False
    assert confidence > 0.7


def test_should_refuse_low_confidence():
    assert should_refuse(0.5) is True


def test_should_refuse_high_confidence():
    assert should_refuse(0.9) is False
