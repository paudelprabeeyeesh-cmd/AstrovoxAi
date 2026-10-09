from alignment.human_preference_learner import HumanPreferenceLearner


class TestHumanPreferenceLearner:
    def test_learn_from_feedback_updates(self):
        hpl = HumanPreferenceLearner(learning_rate=1.0)
        hpl.learn_from_feedback("action_a", human_score=0.9)
        assert abs(hpl.preferences["action_a"] - 0.9) < 1e-6

    def test_learn_from_feedback_partial(self):
        hpl = HumanPreferenceLearner(learning_rate=0.5)
        hpl.preferences["action_a"] = 0.5
        hpl.learn_from_feedback("action_a", human_score=1.0)
        expected = 0.5 * 0.5 + 1.0 * 0.5
        assert abs(hpl.preferences["action_a"] - expected) < 1e-6

    def test_preference_ranking_ordering(self):
        hpl = HumanPreferenceLearner()
        hpl.preferences = {"a": 0.3, "b": 0.8, "c": 0.5}
        assert hpl.preference_ranking() == ["b", "c", "a"]

    def test_confidence_weighted_score_missing(self):
        hpl = HumanPreferenceLearner()
        assert hpl.confidence_weighted_score("missing") == 0.5

    def test_exploration_choice_returns_option(self):
        hpl = HumanPreferenceLearner()
        hpl.preferences = {"a": 0.9}
        choice = hpl.exploration_choice()
        assert choice in hpl.preferences

    def test_average_feedback_quality_empty(self):
        hpl = HumanPreferenceLearner()
        assert hpl.average_feedback_quality() == 0.0

    def test_average_feedback_quality_nonempty(self):
        hpl = HumanPreferenceLearner()
        hpl.feedback_history.append({"previous_score": 0.0, "human_score": 0.5})
        assert abs(hpl.average_feedback_quality() - 0.5) < 1e-6
