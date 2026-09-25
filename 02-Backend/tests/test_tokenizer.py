import os
import tempfile
from app.core.tokenizer import BPETokenizer


def test_train_bpe_small_corpus():
    tokenizer = BPETokenizer()
    corpus = "hello world hello there"
    vocab_size = 300
    tokenizer.train_bpe(corpus, vocab_size)

    assert tokenizer.get_vocab_size() >= 260
    assert tokenizer.get_vocab_size() <= vocab_size
    assert 0 in tokenizer.vocab
    assert 255 in tokenizer.vocab
    assert tokenizer.SPECIAL_TOKENS["<|BOS|>"] in tokenizer.vocab
    assert tokenizer.SPECIAL_TOKENS["<|EOS|>"] in tokenizer.vocab
    assert tokenizer.SPECIAL_TOKENS["<|PAD|>"] in tokenizer.vocab
    assert tokenizer.SPECIAL_TOKENS["<|UNK|>"] in tokenizer.vocab
    assert len(tokenizer.merges) == tokenizer.get_vocab_size() - 260


def test_encode_decode_roundtrip():
    tokenizer = BPETokenizer()
    corpus = "hello world hello there"
    tokenizer.train_bpe(corpus, 300)

    text = "hello world"
    ids = tokenizer.encode(text)
    decoded = tokenizer.decode(ids)

    assert decoded == text


def test_special_tokens():
    tokenizer = BPETokenizer()
    corpus = "hello world"
    tokenizer.train_bpe(corpus, 300)

    ids = tokenizer.encode("hello", add_bos=True, add_eos=True)
    assert ids[0] == tokenizer.SPECIAL_TOKENS["<|BOS|>"]
    assert ids[-1] == tokenizer.SPECIAL_TOKENS["<|EOS|>"]

    ids = tokenizer.encode("hello", add_bos=True)
    assert ids[0] == tokenizer.SPECIAL_TOKENS["<|BOS|>"]

    ids = tokenizer.encode("hello", add_eos=True)
    assert ids[-1] == tokenizer.SPECIAL_TOKENS["<|EOS|>"]


def test_unicode_handling():
    tokenizer = BPETokenizer()
    corpus = "Hello 世界 🌍"
    tokenizer.train_bpe(corpus, 300)

    ids = tokenizer.encode(corpus)
    decoded = tokenizer.decode(ids)
    assert decoded == corpus


def test_vocab_size_matches_expected():
    tokenizer = BPETokenizer()
    corpus = (
        "The quick brown fox jumps over the lazy dog. "
        "Hello 世界 🌍. Pack my box with five dozen liquor jugs. "
        "How vexingly quick daft zebras jump! "
        "The five boxing wizards jump quickly. "
    ) * 200
    expected_size = 395
    tokenizer.train_bpe(corpus, expected_size)

    assert tokenizer.get_vocab_size() == expected_size


def test_save_load():
    tokenizer = BPETokenizer()
    corpus = "hello world hello there"
    tokenizer.train_bpe(corpus, 300)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name

    try:
        tokenizer.save(path)

        new_tokenizer = BPETokenizer()
        new_tokenizer.load(path)

        assert new_tokenizer.get_vocab_size() == tokenizer.get_vocab_size()
        assert new_tokenizer.merges == tokenizer.merges
        assert new_tokenizer.vocab == tokenizer.vocab

        text = "hello world"
        ids = new_tokenizer.encode(text)
        decoded = new_tokenizer.decode(ids)
        assert decoded == text
    finally:
        os.remove(path)


def test_unk_token_handling():
    tokenizer = BPETokenizer()
    corpus = "hello world"
    tokenizer.train_bpe(corpus, 300)

    ids = tokenizer.encode(corpus)
    decoded = tokenizer.decode(ids)
    assert decoded == corpus


def test_empty_text():
    tokenizer = BPETokenizer()
    corpus = "hello"
    tokenizer.train_bpe(corpus, 300)

    ids = tokenizer.encode("")
    assert ids == []

    ids = tokenizer.encode("", add_bos=True)
    assert ids == [tokenizer.SPECIAL_TOKENS["<|BOS|>"]]

    ids = tokenizer.encode("", add_eos=True)
    assert ids == [tokenizer.SPECIAL_TOKENS["<|EOS|>"]]


def test_single_character():
    tokenizer = BPETokenizer()
    corpus = "a"
    tokenizer.train_bpe(corpus, 300)

    ids = tokenizer.encode("a")
    assert len(ids) == 1
    decoded = tokenizer.decode(ids)
    assert decoded == "a"


def test_merge_count_matches_vocab_size():
    tokenizer = BPETokenizer()
    corpus = (
        "The quick brown fox jumps over the lazy dog. "
        "Hello 世界 🌍. Pack my box with five dozen liquor jugs. "
        "How vexingly quick daft zebras jump! "
        "The five boxing wizards jump quickly. "
    ) * 200
    vocab_size = 395
    tokenizer.train_bpe(corpus, vocab_size)

    assert len(tokenizer.merges) == tokenizer.get_vocab_size() - 260


def test_encode_returns_int_ids():
    tokenizer = BPETokenizer()
    corpus = "hello world"
    tokenizer.train_bpe(corpus, 300)

    ids = tokenizer.encode("hello world")
    assert all(isinstance(id_, int) for id_ in ids)
