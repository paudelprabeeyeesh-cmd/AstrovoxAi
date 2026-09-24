from diff_patch_engine.patch_applier import PatchApplier


def test_apply_search_replace_success():
    content = "hello world foo bar"
    result = PatchApplier.apply_search_replace(content, "hello", "hi")
    assert result["success"] is True
    assert result["conflict"] is False
    assert result["result"] == "hi world foo bar"


def test_apply_search_replace_not_found():
    content = "hello world"
    result = PatchApplier.apply_search_replace(content, "xyz", "hi")
    assert result["success"] is False
    assert result["conflict"] is True
    assert result["result"] == content


def test_apply_search_replace_not_unique():
    content = "hello world hello foo"
    result = PatchApplier.apply_search_replace(content, "hello", "hi")
    assert result["success"] is False
    assert result["conflict"] is True
    assert result["result"] == content


def test_apply_search_replace_occurrences_count():
    content = "hello world hello foo"
    result = PatchApplier.apply_search_replace(content, "hello", "hi")
    assert result["old_text_occurrences"] == 2


def test_apply_unified_hunks_success():
    original = "line1\nline2\nline3\n"
    diff_text = "--- original\n+++ rewritten\n@@ -2,1 +2,2 @@\n-line2\n+line2_modified\n+line3_extra\n"
    from diff_patch_engine.unified_diff import UnifiedDiffGenerator
    hunks = UnifiedDiffGenerator.parse(diff_text)
    result = PatchApplier.apply_unified_hunks(original, hunks)
    assert result["success"] is True
    assert "line2_modified" in result["result"]
    assert "line3_extra" in result["result"]


def test_apply_unified_hunks_not_unique():
    original = "hello world hello foo"
    hunks = [(1, 5, 1, 1, "hello", "hi")]
    result = PatchApplier.apply_unified_hunks(original, hunks)
    assert result["success"] is False
    assert result["conflict"] is True


def test_apply_diff_text_success():
    original = "line1\nline2\nline3\n"
    diff_text = "--- original\n+++ rewritten\n@@ -2,1 +2,2 @@\n-line2\n+line2_modified\n+line3_extra\n"
    result = PatchApplier.apply_diff_text(original, diff_text)
    assert result["success"] is True
    assert "line2_modified" in result["result"]


def test_apply_patch_search_replace_type():
    content = "hello world"
    patch = {"type": "search_replace", "old_text": "hello", "new_text": "hi"}
    result = PatchApplier.apply_patch(content, patch)
    assert result["success"] is True
    assert result["result"] == "hi world"


def test_apply_patch_unsupported_type():
    content = "hello world"
    patch = {"type": "unknown", "old_text": "hello", "new_text": "hi"}
    result = PatchApplier.apply_patch(content, patch)
    assert result["success"] is False
    assert result["conflict"] is True


def test_batch_apply_all_success():
    content = "a b c d"
    patches = [
        {"type": "search_replace", "old_text": "a", "new_text": "x"},
        {"type": "search_replace", "old_text": "c", "new_text": "y"},
    ]
    result = PatchApplier.batch_apply(content, patches)
    assert result["success"] is True
    assert result["result"] == "x b y d"
    assert len(result["applied"]) == 2
    assert result["conflicts"] == []


def test_batch_apply_conflict():
    content = "a a c d"
    patches = [
        {"type": "search_replace", "old_text": "a", "new_text": "x"},
    ]
    result = PatchApplier.batch_apply(content, patches)
    assert result["success"] is False
    assert len(result["conflicts"]) > 0


def test_batch_apply_chain():
    content = "hello world foo bar"
    patches = [
        {"type": "search_replace", "old_text": "hello", "new_text": "hi"},
        {"type": "search_replace", "old_text": "foo", "new_text": "baz"},
    ]
    result = PatchApplier.batch_apply(content, patches)
    assert result["result"] == "hi world baz bar"


def test_apply_search_replace_with_newlines():
    original = "def foo():\n    x = 1\n    return x\n"
    patch_result = PatchApplier.apply_search_replace(
        original, "    x = 1\n", "    x = 2\n"
    )
    assert patch_result["success"] is True
    assert "    x = 2\n" in patch_result["result"]


def test_apply_diff_text_conflict_not_unique():
    original = "hello hello world"
    diff_text = "--- original\n+++ rewritten\n@@ -1,1 +1,1 @@\n-hello\n+hi\n"
    result = PatchApplier.apply_diff_text(original, diff_text)
    assert result["conflict"] is True
    assert result["success"] is False
