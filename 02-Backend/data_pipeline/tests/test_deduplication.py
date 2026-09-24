import unittest

from numpy.testing import assert_array_equal

from data_pipeline.deduplication import MinHashLSH


class TestMinHashLSH(unittest.TestCase):
    def test_init(self):
        lsh = MinHashLSH(num_hashes=100, num_bands=10)
        self.assertEqual(lsh.num_hashes, 100)
        self.assertEqual(lsh.num_bands, 10)
        self.assertEqual(lsh.rows_per_band, 10)

    def test_shingle(self):
        lsh = MinHashLSH()
        shingles = lsh._shingle("hello", k=2)
        self.assertEqual(shingles, ["he", "el", "ll", "lo"])

    def test_signature(self):
        lsh = MinHashLSH(num_hashes=2)
        shingles = lsh._shingle("hello", k=2)
        sig = lsh._signature(shingles)
        self.assertEqual(len(sig), 2)
        self.assertIsInstance(sig[0], int)

    def test_add(self):
        lsh = MinHashLSH()
        lsh.add("doc1", "hello world")
        self.assertEqual(len(lsh._buckets), 10)

    def test_query_empty(self):
        lsh = MinHashLSH()
        result = lsh.query("hello world")
        self.assertEqual(result, [])

    def test_query_duplicate(self):
        lsh = MinHashLSH(num_hashes=10, num_bands=1)
        lsh.add("doc1", "hello world test")
        result = lsh.query("hello world test", threshold=0.5)
        self.assertEqual(result, ["doc1"])

    def test_query_non_duplicate(self):
        lsh = MinHashLSH(num_hashes=10, num_bands=1)
        lsh.add("doc1", "hello world")
        result = lsh.query("completely different text here", threshold=0.5)
        self.assertEqual(result, [])

    def test_jaccard(self):
        lsh = MinHashLSH()
        a = [1, 2, 3]
        b = [1, 2, 4]
        sim = lsh._jaccard(a, b)
        self.assertAlmostEqual(sim, 2.0 / 3.0)

    def test_jaccard_empty(self):
        lsh = MinHashLSH()
        self.assertEqual(lsh._jaccard([], [1, 2, 3]), 0.0)
