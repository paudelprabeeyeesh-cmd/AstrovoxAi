from agentic_loop.observation_normalization import (
    ObservationNormalizer,
)


def test_normalizer_truncation():
    norm = ObservationNormalizer(max_length=20)
    raw = " ".join(str(i) for i in range(50))
    result = norm.normalize(raw, "test")
    assert result.truncated is True
    assert result.truncated is True
    assert result.original == raw


def test_normalizer_no_truncation_when_short():
    norm = ObservationNormalizer(max_length=500)
    raw = "short output"
    result = norm.normalize(raw, "test")
    assert result.truncated is False
    assert result.normalized == raw


def test_normalizer_preserves_tokens():
    norm = ObservationNormalizer(max_length=20)
    raw = "value 3.14 is ABC and \"hello\""
    result = norm.normalize(raw, "test")
    assert "3.14" in result.normalized or "[3.14]" in result.normalized
    assert "ABC" in result.normalized or "[ABC]" in result.normalized


def test_normalizer_whitespace_cleanup():
    norm = ObservationNormalizer(max_length=500)
    raw = "  hello   world\t\nfoo  "
    result = norm.normalize(raw, "test")
    assert result.normalized == "hello world foo"


def test_normalizer_token_count():
    norm = ObservationNormalizer(max_length=500)
    raw = "one two three"
    result = norm.normalize(raw, "test")
    assert len(result.normalized.split()) == 3
