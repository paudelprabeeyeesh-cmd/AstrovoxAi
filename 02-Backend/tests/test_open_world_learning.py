import pytest
import numpy as np
from agi_core.open_world_learning import OpenWorldLearner


class TestOpenWorldLearner:
    def test_learn_concept(self):
        learner = OpenWorldLearner()
        c = learner.learn_concept("gravity", "physics")
        assert c.confidence == 0.5

    def test_transfer(self):
        learner = OpenWorldLearner()
        learner.learn_concept("gravity", "physics")
        tc = learner.transfer("gravity", "engineering")
        assert tc is not None
        assert tc.domain == "engineering"

    def test_generalize(self):
        learner = OpenWorldLearner()
        learner.learn_concept("cat", "biology")
        learner.learn_concept("dog", "biology")
        g = learner.generalize(["cat", "dog"])
        assert isinstance(g, np.ndarray)

    def test_query(self):
        learner = OpenWorldLearner()
        learner.learn_concept("test", "general")
        matches = learner.query("test")
        assert isinstance(matches, list)
