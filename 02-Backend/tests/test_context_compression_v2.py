"""Tests for context compression."""

import pytest
from unittest.mock import MagicMock, patch

from app.context_compression import (
    ContextCompressor,
    CompressionStrategy,
    CompressionResult,
)


class TestContextCompressor:
    def test_compress_skips_when_small(self):
        compressor = ContextCompressor()
        result = compressor.compress(context="short", max_tokens=1000)
        assert result.compressed == "short"
        assert result.metadata.get("skipped") is True

    def test_estimate_tokens_fallback(self):
        compressor = ContextCompressor()
        tokens = compressor.estimate_tokens("hello world")
        assert tokens >= 1

    def test_heuristic_extract(self):
        compressor = ContextCompressor()
        context = "Python is great. The sky is blue. Code is fun."
        result = compressor.extract_important(context, query="python code")
        assert "Python" in result or "Code" in result

    def test_heuristic_compress(self):
        compressor = ContextCompressor()
        text = "a" * 1000
        result = compressor._heuristic_compress(text, max_tokens=100)
        assert compressor.estimate_tokens(result) <= 250

    def test_abstractive_compress_success(self):
        compressor = ContextCompressor()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "compressed summary"
        mock_client.chat.completions.create.return_value = mock_response
        compressor._client = mock_client
        result = compressor._abstractive_compress("a" * 1000, max_tokens=100)
        assert result.compressed == "compressed summary"
        assert result.strategy == CompressionStrategy.ABSTRACTIVE

    def test_extractive_compress_success(self):
        compressor = ContextCompressor()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "extracted sentence"
        mock_client.chat.completions.create.return_value = mock_response
        compressor._client = mock_client
        result = compressor._extractive_compress("a" * 1000, max_tokens=100, query="sentence")
        assert result.compressed == "extracted sentence"
        assert result.strategy == CompressionStrategy.EXTRACTIVE

    def test_hybrid_compress_falls_back(self):
        compressor = ContextCompressor()
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("fail")
        compressor._client = mock_client
        result = compressor._hybrid_compress("a" * 1000, max_tokens=100, query="anything")
        assert result.compressed
        assert result.metadata.get("fallback") == "heuristic"
