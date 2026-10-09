
from app.evaluation.toxicity import ToxicityEvaluator


def test_toxicity_clean():
    evaluator = ToxicityEvaluator()
    result = evaluator.evaluate("Hello, how are you today?")
    assert result["score"] == 1.0
    assert result["risk_level"] == "low"


def test_toxicity_detects_hate():
    evaluator = ToxicityEvaluator()
    result = evaluator.evaluate("I hate you and want to attack you.")
    assert result["score"] < 1.0
    assert result["toxic_terms_found"] >= 1
    assert result["risk_level"] == "high"


def test_toxicity_severity():
    evaluator = ToxicityEvaluator()
    assert evaluator.severity("You are great!") == "low"
