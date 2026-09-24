"""Tests for the self-correction loop."""

import pytest
from unittest.mock import MagicMock, patch

from app.self_correction import SelfCorrectionLoop, SelfCorrectionResult


class TestSelfCorrectionResult:
    def test_defaults(self):
        result = SelfCorrectionResult(original="a", corrected="a", confidence=1.0, issues=[], passes=0)
        assert result.metadata == {}


class TestSelfCorrectionLoop:
    def test_review_no_issues(self):
        loop = SelfCorrectionLoop()
        result = loop.review(response="short response")
        assert result.corrected == "short response"
        assert result.issues == []
        assert result.confidence == 1.0

    def test_review_empty_response(self):
        loop = SelfCorrectionLoop()
        result = loop.review(response="")
        assert result.corrected == "I couldn't generate a response. Please try again."
        assert result.passes >= 1

    def test_review_too_long(self):
        loop = SelfCorrectionLoop()
        long_text = "x" * 5000
        result = loop.review(response=long_text)
        assert "too_long" in result.issues
        assert result.corrected.endswith("...")

    def test_review_unsupported_claim_without_context(self):
        loop = SelfCorrectionLoop()
        result = loop.review(response="some claim")
        assert result.corrected == "some claim"
        assert result.passes == 0

    def test_review_unsupported_claim_with_context(self):
        loop = SelfCorrectionLoop()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "revised response"
        mock_client.chat.completions.create.return_value = mock_response
        loop._client = mock_client
        result = loop.review(response="some claim", context="context supports revised")
        assert result.corrected == "revised response"
        assert "unsupported_claim" in result.issues

    def test_review_applies_correction_and_stops(self):
        loop = SelfCorrectionLoop(max_passes=2)
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "fixed"
        mock_client.chat.completions.create.return_value = mock_response
        loop._client = mock_client
        result = loop.review(response="some claim", context="ctx")
        assert result.passes >= 1
        assert result.corrected == "fixed"

    def test_confidence_from_issues(self):
        loop = SelfCorrectionLoop()
        assert loop._confidence_from_issues([], "ok") == 1.0
        assert loop._confidence_from_issues(["a", "b"], "ok") == pytest.approx(0.6)
