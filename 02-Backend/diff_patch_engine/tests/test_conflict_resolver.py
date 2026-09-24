from diff_patch_engine.conflict_resolver import ConflictResolver


def test_detect_conflicts_non_unique_old_text():
    original = "hello world hello foo"
    source_patch = {"type": "search_replace", "old_text": "hello", "new_text": "hi"}
    dest_patch = {"type": "search_replace", "old_text": "world", "new_text": "earth"}
    conflicts = ConflictResolver.detect_conflicts(source_patch, dest_patch, original)
    assert len(conflicts) == 1
    assert conflicts[0].kind == "non_unique"


def test_detect_conflicts_none():
    original = "hello world foo"
    source_patch = {"type": "search_replace", "old_text": "hello", "new_text": "hi"}
    dest_patch = {"type": "search_replace", "old_text": "world", "new_text": "earth"}
    conflicts = ConflictResolver.detect_conflicts(source_patch, dest_patch, original)
    assert conflicts == []


def test_resolve_conflicts_strategy_source():
    original = "hello world foo"
    source_patch = {"type": "search_replace", "old_text": "hello", "new_text": "hi"}
    dest_patch = {"type": "search_replace", "old_text": "world", "new_text": "earth"}
    result = ConflictResolver.resolve_conflicts(
        original, source_patch, dest_patch, strategy="source"
    )
    assert result["strategy"] == "source"
    assert result["result"] == "hi world foo"


def test_resolve_conflicts_strategy_destination():
    original = "hello world foo"
    source_patch = {"type": "search_replace", "old_text": "hello", "new_text": "hi"}
    dest_patch = {"type": "search_replace", "old_text": "world", "new_text": "earth"}
    result = ConflictResolver.resolve_conflicts(
        original, source_patch, dest_patch, strategy="destination"
    )
    assert result["strategy"] == "destination"
    assert result["result"] == "hello earth foo"


def test_resolve_conflicts_strategy_skip():
    original = "hello world foo"
    source_patch = {"type": "search_replace", "old_text": "hello", "new_text": "hi"}
    dest_patch = {"type": "search_replace", "old_text": "world", "new_text": "earth"}
    result = ConflictResolver.resolve_conflicts(
        original, source_patch, dest_patch, strategy="skip"
    )
    assert result["result"] == original
    assert result["strategy"] == "skip"


def test_resolve_conflicts_invalid_strategy():
    original = "hello world foo"
    source_patch = {"type": "search_replace", "old_text": "hello", "new_text": "hi"}
    dest_patch = {"type": "search_replace", "old_text": "world", "new_text": "earth"}
    with Exception():
        ConflictResolver.resolve_conflicts(
            original, source_patch, dest_patch, strategy="invalid"
        )


def test_merge_hunks_combined():
    source = [(1, 1, 1, 1, "a", "x")]
    dest = [(2, 1, 2, 1, "b", "y")]
    merged = ConflictResolver.merge_hunks(source, dest)
    assert len(merged) == 2


def test_merge_hunks_deduplicates():
    hunk = (1, 1, 1, 1, "a", "x")
    source = [hunk]
    dest = [hunk]
    merged = ConflictResolver.merge_hunks(source, dest)
    assert len(merged) == 2


def test_generate_conflict_marker():
    original = "line1\nline2\nline3\n"
    source_patch = {"type": "search_replace", "old_text": "line2\n", "new_text": "line2a\n"}
    dest_patch = {"type": "search_replace", "old_text": "line2\n", "new_text": "line2b\n"}
    marker = ConflictResolver.generate_conflict_marker(original, source_patch, dest_patch)
    assert "<<<<<<< source" in marker
    assert "=======" in marker
    assert ">>>>>>> destination" in marker
    assert "line2a" in marker
    assert "line2b" in marker


def test_generate_conflict_marker_has_source_and_dest():
    original = "hello world foo"
    source_patch = {"type": "search_replace", "old_text": "hello", "new_text": "hi"}
    dest_patch = {"type": "search_replace", "old_text": "world", "new_text": "earth"}
    marker = ConflictResolver.generate_conflict_marker(original, source_patch, dest_patch)
    assert "hi" in marker
    assert "earth" in marker


def test_conflict_class_attributes():
    conflict = ConflictResolver.Conflict(
        kind="non_unique", description="old_text not unique", source="source_patch"
    )
    assert conflict.kind == "non_unique"
    assert conflict.description == "old_text not unique"
    assert conflict.source == "source_patch"


def test_detect_conflicts_multiple_non_unique():
    original = "a a b b c"
    source_patch = {"type": "search_replace", "old_text": "a", "new_text": "x"}
    dest_patch = {"type": "search_replace", "old_text": "b", "new_text": "y"}
    conflicts = ConflictResolver.detect_conflicts(source_patch, dest_patch, original)
    assert len(conflicts) == 2
    kinds = [c.kind for c in conflicts]
    assert "non_unique" in kinds


def test_resolve_conflicts_no_apply_changes_skip():
    original = "line1\nline2\nline3\n"
    source_patch = {"type": "search_replace", "old_text": "line2", "new_text": "2"}
    dest_patch = {"type": "search_replace", "old_text": "line3", "new_text": "3"}
    result = ConflictResolver.resolve_conflicts(
        original, source_patch, dest_patch, strategy="skip"
    )
    assert result["result"] == original


def test_merge_hunks_empty_lists():
    merged = ConflictResolver.merge_hunks([], [])
    assert merged == []


def test_merge_hunks_only_source():
    source = [(1, 1, 1, 1, "a", "x")]
    merged = ConflictResolver.merge_hunks(source, [])
    assert merged == source


def test_merge_hunks_only_dest():
    dest = [(1, 1, 1, 1, "a", "x")]
    merged = ConflictResolver.merge_hunks([], dest)
    assert merged == dest
