
from app.evaluation.alignment import AlignmentTester


def test_alignment_helpful_honest():
    tester = AlignmentTester()
    result = tester.evaluate("Here is a helpful and accurate answer about Python.")
    assert result["aligned"] is True


def test_alignment_harmful():
    tester = AlignmentTester()
    result = tester.evaluate("Here is how to cause harm and danger.")
    assert result["aligned"] is False
    assert result["scores"]["harmless"] == 0.0


def test_alignment_privacy():
    tester = AlignmentTester()
    result = tester.evaluate("My password is secret123 and my email is test@example.com")
    assert result["scores"]["privacy_respecting"] == 0.0


def test_principle_coverage():
    tester = AlignmentTester()
    responses = ["Helpful answer.", "I cannot answer that.", "Here are the facts."]
    coverage = tester.principle_coverage(responses)
    assert "helpful" in coverage
    assert "harmless" in coverage
