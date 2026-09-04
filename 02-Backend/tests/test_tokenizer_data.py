"""Tests for the tokenizer and data pipeline (Stage 40 Program 3)."""

from __future__ import annotations

import unittest

from app.tokenizer_data import (
    DatasetRegistry,
    Deduplicator,
    Document,
    QualityFilter,
    StreamingDataset,
    TextCleaner,
    Tokenizer,
    TokenizerConfig,
    TokenizerTrainingResult,
    train_tokenizer,
)


CORPUS = [
    "the quick brown fox jumps over the lazy dog",
    "the quick brown fox runs through the forest",
    "she sells seashells by the seashore",
    "the rain in spain stays mainly in the plain",
]


class TokenizerTest(unittest.TestCase):
    def test_train_and_encode(self):
        tokenizer = Tokenizer(TokenizerConfig(vocab_size=100, min_pair_freq=1))
        tokenizer.train(CORPUS)
        self.assertGreater(tokenizer.vocab_size, 0)
        ids = tokenizer.encode("the quick fox")
        self.assertGreater(len(ids), 0)
        decoded = tokenizer.decode(ids)
        self.assertIn("fox", decoded)

    def test_vocab_includes_characters(self):
        tokenizer = Tokenizer(TokenizerConfig(vocab_size=50, min_pair_freq=1))
        tokenizer.train(CORPUS)
        # All non-space characters from corpus must be in vocab
        for text in CORPUS:
            for ch in set(text.lower()):
                if ch.strip():  # Skip whitespace
                    self.assertIn(ch, tokenizer.vocab)

    def test_save_and_load(self):
        tokenizer = Tokenizer(TokenizerConfig(vocab_size=50, min_pair_freq=1))
        tokenizer.train(CORPUS)
        saved = tokenizer.save()
        new_tokenizer = Tokenizer()
        new_tokenizer.load(saved)
        ids1 = tokenizer.encode("the quick fox")
        ids2 = new_tokenizer.encode("the quick fox")
        self.assertEqual(ids1, ids2)

    def test_max_token_length_chunking(self):
        tokenizer = Tokenizer(
            TokenizerConfig(vocab_size=50, min_pair_freq=1, max_token_length=4)
        )
        tokenizer.train(CORPUS)
        ids = tokenizer.encode("extraordinarilylongword")
        self.assertGreater(len(ids), 1)

    def test_empty_corpus(self):
        tokenizer = Tokenizer(TokenizerConfig(vocab_size=10))
        tokenizer.train([])
        # Should have no merges
        self.assertEqual(len(tokenizer.merges), 0)


class TextCleanerTest(unittest.TestCase):
    def test_basic_clean(self):
        cleaner = TextCleaner()
        result = cleaner.clean("  hello   world  ")
        self.assertEqual(result, "hello world")

    def test_normalize_unicode(self):
        cleaner = TextCleaner(min_length=2)
        result = cleaner.clean("café")
        self.assertIsNotNone(result)
        self.assertIn("caf", result)

    def test_remove_control(self):
        cleaner = TextCleaner()
        result = cleaner.clean("hello\x00world\x07test")
        self.assertNotIn("\x00", result)
        self.assertNotIn("\x07", result)

    def test_too_short(self):
        cleaner = TextCleaner(min_length=100)
        result = cleaner.clean("short text")
        self.assertIsNone(result)

    def test_too_long(self):
        cleaner = TextCleaner(max_length=10)
        result = cleaner.clean("this is a very long text that exceeds the max length")
        self.assertIsNone(result)

    def test_empty(self):
        cleaner = TextCleaner()
        self.assertIsNone(cleaner.clean(""))


class QualityFilterTest(unittest.TestCase):
    def test_good_text_accepted(self):
        qf = QualityFilter()
        self.assertTrue(qf.accept("This is a perfectly normal English sentence with several words."))

    def test_symbol_heavy_rejected(self):
        qf = QualityFilter()
        self.assertFalse(qf.accept("!!!!@@@@####$$$$"))

    def test_short_words_rejected(self):
        qf = QualityFilter()
        self.assertFalse(qf.accept("a b c d e f"))

    def test_no_alpha_rejected(self):
        qf = QualityFilter()
        self.assertFalse(qf.accept("123 456 789"))

    def test_score(self):
        qf = QualityFilter()
        score = qf.score("Hello world this is a test")
        self.assertGreater(score, 0)


class DeduplicatorTest(unittest.TestCase):
    def test_exact_duplicate(self):
        dedup = Deduplicator()
        self.assertFalse(dedup.is_duplicate("hello world"))
        self.assertTrue(dedup.is_duplicate("hello world"))
        self.assertTrue(dedup.is_duplicate("  hello world  "))  # case + whitespace

    def test_unique_documents(self):
        dedup = Deduplicator()
        self.assertFalse(dedup.is_duplicate("the quick brown fox"))
        self.assertFalse(dedup.is_duplicate("completely different text here"))

    def test_near_duplicate(self):
        dedup = Deduplicator(ngram_size=3)
        text1 = "the quick brown fox jumps over the lazy dog and runs through the forest"
        text2 = "the quick brown fox jumps over the lazy dog and runs through the woods"
        dedup.is_duplicate(text1)
        self.assertTrue(dedup.is_duplicate(text2))


class StreamingDatasetTest(unittest.TestCase):
    def test_basic_pipeline(self):
        docs = [
            Document(id="1", text="the quick brown fox jumps over the lazy dog", source="test"),
            Document(id="2", text="!!!@@@###", source="test"),  # bad quality
            Document(id="3", text="the quick brown fox jumps over the lazy dog", source="test"),  # dup
            Document(id="4", text="she sells seashells by the seashore", source="test"),
        ]
        dataset = StreamingDataset(docs)
        result = list(dataset)
        ids = [d.id for d in result]
        self.assertIn("1", ids)
        self.assertNotIn("2", ids)
        self.assertNotIn("3", ids)
        self.assertIn("4", ids)

    def test_empty_result_for_all_bad(self):
        docs = [Document(id="1", text="x" * 5, source="test")]
        dataset = StreamingDataset(docs)
        self.assertEqual(len(list(dataset)), 0)


class DatasetRegistryTest(unittest.TestCase):
    def test_register_and_get(self):
        reg = DatasetRegistry()
        v = reg.register("v1", num_documents=100, num_tokens=5000)
        self.assertEqual(v.version, "v1")
        self.assertEqual(v.num_documents, 100)
        fetched = reg.get("v1")
        self.assertIsNotNone(fetched)

    def test_lineage(self):
        reg = DatasetRegistry()
        reg.register("v1", 100, 5000)
        reg.register("v2", 200, 10000, parent_version="v1")
        reg.register("v3", 300, 15000, parent_version="v2")
        self.assertIn("v2", reg.lineage("v1"))
        self.assertIn("v3", reg.lineage("v2"))

    def test_list(self):
        reg = DatasetRegistry()
        reg.register("v1", 100, 5000)
        reg.register("v2", 200, 10000)
        self.assertEqual(len(reg.list()), 2)


class TokenizerTrainingTest(unittest.TestCase):
    def test_train(self):
        result = train_tokenizer(CORPUS, TokenizerConfig(vocab_size=100, min_pair_freq=1))
        self.assertIsInstance(result, TokenizerTrainingResult)
        self.assertGreater(result.vocab_size, 0)
        self.assertGreater(result.corpus_size, 0)
        self.assertGreater(result.num_merges, 0)


if __name__ == "__main__":
    unittest.main()
