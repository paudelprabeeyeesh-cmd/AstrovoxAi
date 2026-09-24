from diff_patch_engine.uniqueness_enforcement import UniquenessEnforcer


def test_count_occurrences():
    text = "hello world hello foo"
    assert UniquenessEnforcer.count_occurrences(text, "hello") == 2
    assert UniquenessEnforcer.count_occurrences(text, "foo") == 1
    assert UniquenessEnforcer.count_occurrences(text, "xyz") == 0


def test_is_unique_true():
    text = "hello world foo"
    assert UniquenessEnforcer.is_unique(text, "hello") is True
    assert UniquenessEnforcer.is_unique(text, "world") is True


def test_is_unique_false():
    text = "hello world foo"
    assert UniquenessEnforcer.is_unique(text, "xyz") is False
    assert UniquenessEnforcer.is_unique(text, "") is False


def test_enforce_returns_position():
    text = "hello world foo"
    pos = UniquenessEnforcer.enforce(text, "hello")
    assert pos == 0
    pos = UniquenessEnforcer.enforce(text, "world")
    assert pos == 6


def test_enforce_returns_none_when_not_unique():
    text = "hello world hello"
    assert UniquenessEnforcer.enforce(text, "hello") is None


def test_enforce_returns_none_when_missing():
    text = "hello world"
    assert UniquenessEnforcer.enforce(text, "xyz") is None


def test_get_all_positions():
    text = "a b a c a"
    positions = UniquenessEnforcer.get_all_positions(text, "a")
    assert positions == [0, 4, 8]


def test_get_all_positions_none():
    text = "hello world"
    positions = UniquenessEnforcer.get_all_positions(text, "x")
    assert positions == []


def test_validate_patch_valid():
    text = "hello world foo bar"
    result = UniquenessEnforcer.validate_patch("hello", text)
    assert result["valid"] is True
    assert result["occurrences"] == 1
    assert result["positions"] == [0]


def test_validate_patch_invalid():
    text = "hello world hello foo"
    result = UniquenessEnforcer.validate_patch("hello", text)
    assert result["valid"] is False
    assert result["occurrences"] == 2


def test_validate_patch_missing():
    text = "hello world"
    result = UniquenessEnforcer.validate_patch("xyz", text)
    assert result["valid"] is False
    assert result["occurrences"] == 0
    assert result["positions"] == []
