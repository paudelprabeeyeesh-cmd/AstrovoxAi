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


def test_compression_ratio():
    cc = ContextCompressor()
    assert cc.compression_ratio("one two three", "one two") == 2.0 / 3.0
    assert cc.compression_ratio("", "x") == 1.0
