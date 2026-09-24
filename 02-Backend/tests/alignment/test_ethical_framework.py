from alignment.ethical_framework import EthicalFramework


class TestEthicalFramework:
    def test_ethical_score_unregistered(self):
        ef = EthicalFramework()
        assert ef.ethical_score({"fairness": 1.0}) == 1.0

    def test_ethical_score_registered(self):
        ef = EthicalFramework()
        ef.register_principle("fairness", weight=0.8)
        ef.register_principle("beneficence", weight=0.6)
        assert 0.0 <= ef.ethical_score({"fairness": 0.7, "beneficence": 0.9}) <= 1.0

    def test_detect_violations_above_threshold(self):
        ef = EthicalFramework()
        ef.register_principle("transparency")
        assert "transparency" not in ef.detect_violations({"transparency": 1.0}, threshold=0.3)

    def test_detect_violations_below_threshold(self):
        ef = EthicalFramework()
        ef.register_principle("transparency")
        assert "transparency" in ef.detect_violations({"transparency": 0.1}, threshold=0.3)

    def test_weighted_compliance_no_violations(self):
        ef = EthicalFramework()
        ef.register_principle("fairness")
        assert abs(ef.weighted_compliance({"fairness": 0.9}) - 0.9) < 1e-6

    def test_weighted_compliance_with_violations(self):
        ef = EthicalFramework()
        ef.register_principle("fairness")
        score = ef.weighted_compliance({"fairness": 0.05})
        assert 0.0 <= score < 1.0

    def test_compliance_rate_initial(self):
        ef = EthicalFramework()
        assert ef.compliance_rate() == 1.0

    def test_compliance_rate_after_violations(self):
        ef = EthicalFramework()
        ef.register_principle("fairness")
        ef.detect_violations({"fairness": 0.05}, threshold=0.3)
        assert 0.0 <= ef.compliance_rate() <= 1.0
