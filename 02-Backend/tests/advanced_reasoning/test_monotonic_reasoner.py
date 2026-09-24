import pytest
from advanced_reasoning.monotonic_reasoner import MonotonicReasoner, Premise, Conclusion


class TestMonotonicReasoner:
    def test_add_premise_creates_conclusion(self):
        reasoner = MonotonicReasoner()
        p = Premise(id="p1", content="rain falls", confidence=0.9)
        conclusions = reasoner.add_premise(p)
        assert len(conclusions) == 1
        assert conclusions[0].content == "rain falls"
        assert p.id in conclusions[0].support

    def test_premises_stored(self):
        reasoner = MonotonicReasoner()
        p = Premise(id="p1", content="test")
        reasoner.add_premise(p)
        assert "p1" in reasoner.premises

    def test_conclusions_accumulate(self):
        reasoner = MonotonicReasoner()
        p1 = Premise(id="p1", content="cats are mammals")
        p2 = Premise(id="p2", content="dogs are mammals")
        reasoner.add_premise(p1)
        reasoner.add_premise(p2)
        assert len(reasoner.get_conclusions()) == 2

    def test_monotonicity_flag(self):
        reasoner = MonotonicReasoner()
        assert reasoner.is_monotonic() is True

    def test_confidence_increases_on_shared_words(self):
        reasoner = MonotonicReasoner()
        p1 = Premise(id="p1", content="the cat sat", confidence=0.9)
        p2 = Premise(id="p2", content="the cat runs")
        reasoner.add_premise(p1)
        conclusions = reasoner.add_premise(p2)
        assert len(conclusions) == 1
        assert conclusions[0].confidence > p1.confidence

    def test_get_conclusions_returns_list(self):
        reasoner = MonotonicReasoner()
        p = Premise(id="p1", content="fact")
        reasoner.add_premise(p)
        cs = reasoner.get_conclusions()
        assert isinstance(cs, list)
        assert all(isinstance(c, Conclusion) for c in cs)
