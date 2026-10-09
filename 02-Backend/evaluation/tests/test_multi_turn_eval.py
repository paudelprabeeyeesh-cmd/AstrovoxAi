
from app.evaluation.multi_turn_eval import MultiTurnEvaluator


def test_multi_turn_evaluation():
    evaluator = MultiTurnEvaluator()
    turns = [
        {"user": "Hello", "assistant": "Hi there!", "context_used": True},
        {"user": "What is 2+2?", "assistant": "It is 4.", "context_used": True},
        {"user": "Thanks", "assistant": "You're welcome.", "context_used": True},
    ]
    result = evaluator.evaluate_conversation(turns)
    assert result["turns"] == 3
    assert result["avg_score"] >= 0.0
    assert result["passed"] is True


def test_multi_turn_empty():
    evaluator = MultiTurnEvaluator()
    result = evaluator.evaluate_conversation([])
    assert result["turns"] == 0
    assert result["avg_score"] == 0.0
