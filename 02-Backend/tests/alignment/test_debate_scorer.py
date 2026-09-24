from alignment.debate_scorer import DebateScorer


class TestDebateScorer:
    def test_argument_coherence_overlap(self):
        ds = DebateScorer()
        score = ds.argument_coherence("fairness is good", "fairness matters")
        assert score > 0.0

    def test_force_score_method_penalty(self):
        ds = DebateScorer()
        manip_score = ds.force_score("trust me", "manipulation")
        evid_score = ds.force_score("data shows", "evidence")
        assert manip_score <= evid_score

    def test_agreement_score_identical(self):
        ds = DebateScorer()
        assert abs(ds.agreement_score(["same", "same"]) - 1.0) < 1e-6

    def test_agreement_score_disjoint(self):
        ds = DebateScorer()
        score = ds.agreement_score(["alpha", "beta"])
        assert 0.0 <= score <= 1.0

    def test_debater_reliability_no_history(self):
        ds = DebateScorer()
        assert ds.debater_reliability([]) == 0.5

    def test_debater_reliability_with_history(self):
        ds = DebateScorer()
        history = [{"quality": 0.7}, {"quality": 0.9}]
        assert abs(ds.debater_reliability(history) - 0.8) < 1e-6

    def test_debate_quality_ordering(self):
        ds = DebateScorer()
        high_quality = ds.debate_quality([{"pro": "evidence shows X", "con": "evidence shows X"}])
        low_quality = ds.debate_quality([{"pro": "alpha beta gamma", "con": "delta epsilon zeta"}])
        assert 0.0 <= high_quality <= 1.0
        assert 0.0 <= low_quality <= 1.0

    def test_debate_win_rate_initial(self):
        ds = DebateScorer()
        assert ds.debate_win_rate("alice") == 0.0

    def test_debate_win_rate_after_log(self):
        ds = DebateScorer()
        ds.record_debate("topic", [], "alice", 0.8)
        assert ds.debate_win_rate("alice") == 1.0
