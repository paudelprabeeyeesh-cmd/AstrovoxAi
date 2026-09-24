import unittest

import numpy as np

from data_pipeline.data_mixing import DataMixer


class TestDataMixer(unittest.TestCase):
    def test_init(self):
        mixer = DataMixer()
        self.assertEqual(mixer.source_weights, {})

    def test_init_with_weights(self):
        mixer = DataMixer(source_weights={"a": 2.0})
        self.assertEqual(mixer.source_weights, {"a": 2.0})

    def test_tune(self):
        mixer = DataMixer()
        mixer.tune({"a": 3.0})
        self.assertEqual(mixer.source_weights, {"a": 3.0})

    def test_sample_empty(self):
        mixer = DataMixer()
        result = mixer.sample({}, 5)
        self.assertEqual(result, [])

    def test_sample_returns_correct_length(self):
        mixer = DataMixer()
        sources = {"a": [1, 2, 3]}
        result = mixer.sample(sources, 2)
        self.assertEqual(len(result), 2)

    def test_sample_with_weights(self):
        mixer = DataMixer(source_weights={"a": 1.0})
        sources = {"a": [1, 2, 3]}
        result = mixer.sample(sources, 3)
        self.assertEqual(len(result), 3)

    def test_sample_deterministic(self):
        mixer = DataMixer()
        sources = {"a": [1, 2, 3, 4, 5]}
        result = mixer.sample(sources, 3)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        for item in result:
            self.assertIn(item, [1, 2, 3, 4, 5])
