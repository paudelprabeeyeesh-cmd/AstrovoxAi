
from app.evaluation.adversarial import AdversarialTester


def _runner(prompt: str) -> str:
    return f"Response to: {prompt}"


def test_generate_adversarial_inputs():
    tester = AdversarialTester()
    inputs = tester.generate_adversarial_inputs("hello", count=3)
    assert len(inputs) == 3
    assert inputs[0] == "hello"


def test_test_robustness():
    tester = AdversarialTester()
    result = tester.test_robustness("test prompt", _runner)
    assert "total" in result
    assert "robustness_score" in result
    assert result["total"] == 5
