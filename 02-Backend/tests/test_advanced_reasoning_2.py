from advanced_reasoning.self_evaluation import SelfEvaluator


class TestSelfEvaluator:
    def test_evaluate_basic(self):
        evaluator = SelfEvaluator()
        result = evaluator.evaluate("This is a clear and concise answer.", "User asked a question.", expected="answer")
        assert 0.0 <= result.score <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert "coherence" in result.dimensions

    def test_score_coherence_short(self):
        evaluator = SelfEvaluator()
        score = evaluator._score_coherence("Short.")
        assert score >= 0.0

    def test_score_accuracy_with_expected(self):
        evaluator = SelfEvaluator()
        score = evaluator._score_accuracy("hello world test", "hello world test extra")
        assert 0.0 <= score <= 1.0

    def test_score_conciseness_long(self):
        evaluator = SelfEvaluator()
        long_text = " ".join(["word"] * 600)
        score = evaluator._score_conciseness(long_text)
        assert score <= 0.5

    def test_suggestions_generated(self):
        evaluator = SelfEvaluator()
        result = evaluator.evaluate("Bad", "Context", expected="Expected")
        assert isinstance(result.suggestions, list)

    def test_custom_weights(self):
        evaluator = SelfEvaluator(weights={"coherence": 1.0})
        result = evaluator.evaluate("Good clear answer.", "Context", expected="Good clear answer.")
        assert result.dimensions["coherence"] >= 0.0
