
from app.evaluation.tool_use_eval import ToolUseEvaluator


def test_tool_selection():
    evaluator = ToolUseEvaluator()
    result = evaluator.evaluate_tool_selection(["search", "summarize"], ["search", "summarize"])
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["f1"] == 1.0


def test_tool_selection_partial():
    evaluator = ToolUseEvaluator()
    result = evaluator.evaluate_tool_selection(["search"], ["search", "summarize"])
    assert result["precision"] == 1.0
    assert result["recall"] == 0.5
    assert 0.0 < result["f1"] < 1.0


def test_tool_sequence():
    evaluator = ToolUseEvaluator()
    result = evaluator.evaluate_tool_sequence(["search", "summarize"], ["search", "summarize"])
    assert result["sequence_accuracy"] == 1.0


def test_tool_use_evaluate():
    evaluator = ToolUseEvaluator()
    result = evaluator.evaluate(["search", "summarize"], ["search", "summarize"])
    assert result["passed"] is True
    assert result["overall"] >= 0.6
