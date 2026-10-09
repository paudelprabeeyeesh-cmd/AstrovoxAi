import pytest
from context_management.context_compression import ContextCompressor


class TestContextCompressor:
    def test_invalid_max_compression_ratio(self):
        with pytest.raises(ValueError):
            ContextCompressor(max_compression_ratio=0)
        with pytest.raises(ValueError):
            ContextCompressor(max_compression_ratio=1.5)

    def test_compress_basic(self):
        compressor = ContextCompressor(max_compression_ratio=0.5)
        text = "one two three four five"
        compressed = compressor.compress(text)
        assert compressed == "one two"

    def test_compress_empty(self):
        compressor = ContextCompressor()
        assert compressor.compress("") == ""

    def test_compress_turns(self):
        compressor = ContextCompressor(max_compression_ratio=0.5)
        turns = [
            {"role": "user", "content": "one two three four"},
            {"role": "assistant", "content": "five six seven eight"},
        ]
        compressed = compressor.compress_turns(turns)
        assert compressed[0]["content"] == "one two"
        assert compressed[1]["content"] == "five six"

    def test_compression_ratio(self):
        compressor = ContextCompressor(max_compression_ratio=0.5)
        ratio = compressor.compression_ratio("one two three four", "one two")
        assert ratio == 0.5

    def test_compression_ratio_empty_original(self):
        compressor = ContextCompressor()
        assert compressor.compression_ratio("", "") == 1.0
