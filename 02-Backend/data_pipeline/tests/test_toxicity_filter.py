import unittest

import numpy as np

from data_pipeline.toxicity_filter import ToxicityFilter


class TestToxicityFilter(unittest.TestCase):
    def test_init(self):
        f = ToxicityFilter()
        self.assertIn("hate", f.lexicon)

    def test_init_custom(self):
        f = ToxicityFilter(lexicon={"bad": 1.0})
        self.assertEqual(f.lexicon, {"bad": 1.0})

    def test_score_empty(self):
        f = ToxicityFilter()
        self.assertEqual(f.score(""), 0.0)

    def test_score_non_toxic(self):
        f = ToxicityFilter()
        s = f.score("I love cats")
        self.assertIsInstance(s, float)
        self.assertGreaterEqual(s, 0.0)

    def test_score_toxic(self):
        f = ToxicityFilter()
        s = f.score("I hate you")
        self.assertIsInstance(s, float)

    def test_down_weight_high(self):
        f = ToxicityFilter()
        w = f.down_weight("hate", base_weight=1.0, high_cutoff=0.5, low_cutoff=0.2)
        self.assertLessEqual(w, 0.1)

    def test_down_weight_low(self):
        f = ToxicityFilter()
        w = f.down_weight("I love you", base_weight=1.0, high_cutoff=0.5, low_cutoff=0.1)
        self.assertEqual(w, 1.0)
