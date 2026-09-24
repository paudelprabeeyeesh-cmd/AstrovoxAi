from social_intelligence.negotiation_engine import (
    NegotiationEngine,
    NegotiationState,
    Offer,
)


class TestNegotiationEngine:
    def setup_method(self):
        self.engine = NegotiationEngine()
        self.state = NegotiationState(parties=["buyer", "seller"])

    def test_propose_creates_offer(self):
        offer = self.engine.propose(self.state, "seller", {"price": 100.0, "time": 1.0})
        assert isinstance(offer, Offer)
        assert offer.proposer == "seller"
        assert offer.terms["price"] == 100.0

    def test_round_increments(self):
        self.engine.propose(self.state, "seller", {"price": 100.0})
        assert self.state.round == 1

    def test_evaluate_empty_returns_zero(self):
        empty_state = NegotiationState(parties=["a", "b"])
        assert self.engine.evaluate(empty_state, "a") == 0.0

    def test_evaluate_returns_score(self):
        self.engine.propose(self.state, "seller", {"price": 100.0, "time": 1.0})
        score = self.engine.evaluate(self.state, "buyer")
        assert score > 0.0

    def test_counteroffer_updates_terms(self):
        self.engine.propose(self.state, "seller", {"price": 100.0})
        counter = self.engine.counteroffer(self.state, "buyer", {"price": 90.0})
        assert counter is not None
        assert counter.terms["price"] == 90.0

    def test_counteroffer_none_when_empty(self):
        empty_state = NegotiationState(parties=["a", "b"])
        assert self.engine.counteroffer(empty_state, "a", {"price": 10.0}) is None

    def test_concede_records_amount(self):
        self.engine.concede(self.state, "seller", "price", 5.0)
        assert self.state.concessions["price"] == 5.0

    def test_is_agreement_false_initially(self):
        assert not self.engine.is_agreement(self.state)

    def test_is_agreement_true_when_close(self):
        self.engine.propose(self.state, "seller", {"price": 100.0, "time": 1.0})
        self.engine.propose(self.state, "buyer", {"price": 100.0, "time": 1.0})
        assert self.engine.is_agreement(self.state)

    def test_get_summary_keys(self):
        summary = self.engine.get_summary(self.state)
        assert "round" in summary
        assert "offer_count" in summary
        assert "agreement" in summary
