from context_management.context_compression import ContextCompressor


def test_init_defaults():
    cc = ContextCompressor()
    assert cc.max_compression_ratio == 0.5


def test_init_invalid_ratio():
    for invalid in (0.0, -0.1, 1.1):
        try:
            ContextCompressor(max_compression_ratio=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")


def test_compress():
    cc = ContextCompressor(max_compression_ratio=0.5)
    compressed = cc.compress("one two three four")
    assert compressed == "one two"


def test_compress_empty():
    cc = ContextCompressor()
    assert cc.compress("") == ""


def test_compress_turns():
    cc = ContextCompressor(max_compression_ratio=0.5)
    turns = [{"role": "user", "content": "one two three four"}]
    out = cc.compress_turns(turns)
    assert out[0]["role"] == "user"
    assert out[0]["content"] == "one two"


def test_compress_single_word():
    cc = ContextCompressor(max_compression_ratio=0.5)
    assert cc.compress("hello") == "hello"


def test_compress_ratio_one_keeps_all():
    cc = ContextCompressor(max_compression_ratio=1.0)
    assert cc.compress("one two three") == "one two three"


def test_compress_turns_empty_list():
    cc = ContextCompressor()
    assert cc.compress_turns([]) == []


def test_compress_turns_defaults_role():
    cc = ContextCompressor(max_compression_ratio=0.5)
    turns = [{"content": "one two three four"}]
    out = cc.compress_turns(turns)
    assert out[0]["role"] == "user"
    assert out[0]["content"] == "one two"


def test_compression_ratio_equal_strings():
    cc = ContextCompressor()
    assert cc.compression_ratio("one two", "one two") == 1.0


def test_compress_preserves_at_least_one_word():
    cc = ContextCompressor(max_compression_ratio=0.1)
    assert cc.compress("one two three") == "one"

