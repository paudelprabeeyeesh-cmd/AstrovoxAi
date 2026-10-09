import unittest


from data_pipeline.curriculum_learning import CurriculumLearner


class TestCurriculumLearner(unittest.TestCase):
    def test_init(self):
        learner = CurriculumLearner()
        self.assertEqual(learner.features, ["length", "vocab_richness", "avg_word_length"])

    def test_init_custom_features(self):
        learner = CurriculumLearner(features=["a"])
        self.assertEqual(learner.features, ["a"])

    def test_difficulty_empty(self):
        learner = CurriculumLearner()
        self.assertEqual(learner.difficulty(""), 0.0)

    def test_difficulty_non_empty(self):
        learner = CurriculumLearner()
        d = learner.difficulty("hello world")
        self.assertIsInstance(d, float)
        self.assertGreaterEqual(d, 0.0)

    def test_order_ascending(self):
        learner = CurriculumLearner()
        samples = ["a", "bb", "ccc"]
        ordered = learner.order(samples, ascending=True)
        self.assertEqual(ordered, ["a", "bb", "ccc"])

    def test_order_descending(self):
        learner = CurriculumLearner()
        samples = ["a", "bb", "ccc"]
        ordered = learner.order(samples, ascending=False)
        self.assertEqual(ordered, ["ccc", "bb", "a"])
