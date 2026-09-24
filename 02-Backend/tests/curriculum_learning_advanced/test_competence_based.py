import pytest
from curriculum_learning_advanced.competence_based import CompetenceEstimator, CompetenceConfig


class TestCompetenceEstimator:
    def test_initialization(self):
        est = CompetenceEstimator()
        assert est.get_competence() == 0.0
        assert not est.is_competent()

    def test_update_competence(self):
        est = CompetenceEstimator(CompetenceConfig(window_size=5))
        for score in [0.1, 0.2, 0.3, 0.4, 0.5]:
            est.update(score)
        assert est.get_competence() == pytest.approx(0.3)
        assert est.is_competent()

    def test_reset(self):
        est = CompetenceEstimator()
        est.update(0.9)
        est.reset()
        assert est.get_competence() == 0.0
        assert len(est.scores) == 0

    def test_window_overflow(self):
        est = CompetenceEstimator(CompetenceConfig(window_size=3))
        for score in [0.1, 0.2, 0.3, 0.4]:
            est.update(score)
        assert len(est.scores) == 3
        assert est.get_competence() == pytest.approx(0.3)
