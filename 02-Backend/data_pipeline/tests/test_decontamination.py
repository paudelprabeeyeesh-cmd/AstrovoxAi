import unittest
from unittest.mock import patch

import numpy as np

from data_pipeline.decontamination import Decontaminator


class TestDecontaminator(unittest.TestCase):
    def test_init(self):
        d = Decontaminator(n=5)
        self.assertEqual(d.n, 5)

    def test_ngrams(self):
        d = Decontaminator(n=3)
        ngrams = d._ngrams("hello")
        self.assertEqual(ngrams, ["hel", "ell", "llo"])

    def test_hash_ngrams_static(self):
        d = Decontaminator()
        ngrams = d._ngrams("hello")
        hashed = d.hash_ngrams(ngrams)
        self.assertIsInstance(hashed, np.ndarray)
        self.assertEqual(hashed.dtype, np.uint64)

    def test_overlap_empty_benchmarks(self):
        d = Decontaminator()
        result = d.overlap("hello world", [])
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(len(result), 0)

    def test_overlap_with_benchmarks(self):
        d = Decontaminator(n=3)
        benchmarks = ["hello world", "goodbye world"]
        result = d.overlap("hello world", benchmarks)
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(result.dtype, np.float32)
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0] > 0)

    def test_overlap_empty_text(self):
        d = Decontaminator()
        benchmarks = ["hello world"]
        result = d.overlap("", benchmarks)
        self.assertEqual(result[0], 0.0)
