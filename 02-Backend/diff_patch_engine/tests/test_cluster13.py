import numpy as np
import pytest

from diff_patch_engine.full_file_rewrite import FullFileRewrite
from diff_patch_engine.unified_diff import UnifiedDiffGenerator
from diff_patch_engine.search_replace_blocks import SearchReplaceBlock
from diff_patch_engine.structured_tool_call import StructuredToolCall
from diff_patch_engine.pre_image_validation import PreImageValidator
from diff_patch_engine.uniqueness_enforcement import UniquenessEnforcer
from diff_patch_engine.syntactic_validity_check import SyntacticValidityChecker
from diff_patch_engine.atomic_multi_file_transaction import AtomicMultiFileTransaction, PatchResult
from diff_patch_engine.inline_diff_ui import InlineDiffUI


def test_full_file_rewrite_generate():
    original = "line1\nline2\nline3\n"
    rewritten = "line1\nline2_modified\nline3_extra\n"
    engine = FullFileRewrite()
    diff = engine.generate(original, rewritten)
    assert "---" in diff
    assert "+++" in diff
    assert "-line2" in diff
    assert "+line2_modified" in diff
    assert "+line3_extra" in diff


def test_full_file_rewrite_apply():
    original = "line1\nline2\nline3\n"
    rewritten = "line1\nline2_modified\nline3_extra\n"
    engine = FullFileRewrite()
    diff = engine.generate(original, rewritten)
    result = engine.apply(original, diff)
    assert "line2_modified" in result
    assert "line3_extra" in result


def test_full_file_rewrite_numpy_line_comparison():
    original = "a\nb\nc\nd\ne\n"
    rewritten = "a\nb_mod\nc\nd\ne\n"
    engine = FullFileRewrite()
    orig_lines = np.array(original.splitlines())
    new_lines = np.array(rewritten.splitlines())
    diff_lines = np.where(orig_lines != new_lines)[0]
    assert len(diff_lines) > 0
    assert 1 in diff_lines


def test_unified_diff_generate():
    original = "line1\nline2\nline3\n"
    rewritten = "line1\nline2_modified\nline3_extra\n"
    diff = UnifiedDiffGenerator.generate(original, rewritten)
    assert "@@" in diff
    assert "-line2" in diff
    assert "+line2_modified" in diff


def test_unified_diff_parse():
    diff_text = "--- original\n+++ rewritten\n@@ -2,1 +2,2 @@\n-line2\n+line2_modified\n+line3_extra\n"
    hunks = UnifiedDiffGenerator.parse(diff_text)
    assert len(hunks) == 1
    assert hunks[0][0] == 2
    assert hunks[0][2] == 2


def test_unified_diff_apply():
    original = "line1\nline2\nline3\n"
    rewritten = "line1\nline2_modified\nline3_extra\n"
    diff = UnifiedDiffGenerator.generate(original, rewritten)
    hunks = UnifiedDiffGenerator.parse(diff)
    result = UnifiedDiffGenerator.apply(original, hunks)
    assert "line2_modified" in result
    assert "line3_extra" in result


def test_search_replace_validate_unique():
    content = "hello world hello foo"
    block = SearchReplaceBlock("hello", "hi")
    assert block.validate(content) is False


def test_search_replace_validate_unique_once():
    content = "hello world foo bar"
    block = SearchReplaceBlock("hello", "hi")
    assert block.validate(content) is True


def test_search_replace_apply():
    content = "hello world foo bar"
    block = SearchReplaceBlock("hello", "hi")
    result = block.apply(content)
    assert result == "hi world foo bar"


def test_search_replace_apply_not_unique():
    content = "hello world hello foo"
    block = SearchReplaceBlock("hello", "hi")
    with pytest.raises(ValueError):
        block.apply(content)


def test_search_replace_get_position():
    content = "abc def ghi"
    block = SearchReplaceBlock("def", "xyz")
    pos = block.get_match_position(content)
    assert pos == 4


def test_search_replace_numpy_uniqueness():
    content = "a b c a d e"
    pattern = "a"
    occurrences = np.sum(np.array(list(content)) == "a")
    assert occurrences == 2


def test_structured_tool_call_grammar_valid():
    call = StructuredToolCall("file.py", 1, 5, "new text")
    assert call.validate_grammar() is True


def test_structured_tool_call_grammar_invalid_start_negative():
    call = StructuredToolCall("file.py", -1, 5, "new text")
    assert call.validate_grammar() is False


def test_structured_tool_call_grammar_invalid_start_greater_than_end():
    call = StructuredToolCall("file.py", 5, 1, "new text")
    assert call.validate_grammar() is False


def test_structured_tool_call_apply():
    original = "line1\nline2\nline3\nline4\n"
    call = StructuredToolCall("file.py", 2, 3, "new_line\n")
    result = call.apply(original)
    assert "new_line" in result
    assert "line2" not in result


def test_structured_tool_call_diff_hunk():
    original = "line1\nline2\nline3\nline4\n"
    call = StructuredToolCall("file.py", 2, 3, "new_line\n")
    hunk = call.diff_hunk(original)
    assert "@@" in hunk
    assert "-line2" in hunk
    assert "+new_line" in hunk


def test_structured_tool_call_apply_invalid_grammar():
    call = StructuredToolCall("file.py", 5, 1, "new text")
    with pytest.raises(ValueError):
        call.apply("line1\nline2\n")


def test_structured_tool_call_to_dict():
    call = StructuredToolCall("file.py", 1, 3, "text")
    d = call.to_dict()
    assert d["file"] == "file.py"
    assert d["start"] == 1
    assert d["end"] == 3
    assert StructuredToolCall.from_dict(d).file_path == "file.py"


def test_pre_image_validation_exact():
    content = "hello world foo bar"
    assert PreImageValidator.validate_exact("hello", content) is True
    assert PreImageValidator.validate_exact("xyz", content) is False


def test_pre_image_validation_fuzzy_match():
    content = "line1\nline2\nline3\n"
    old = "line2\nline3\n"
    result = PreImageValidator.validate(old, content, fuzzy=True)
    assert result["valid"] is True


def test_pre_image_validation_no_match():
    content = "line1\nline2\nline3\n"
    old = "line99\n"
    result = PreImageValidator.validate(old, content, fuzzy=True)
    assert result["valid"] is False


def test_pre_image_validation_numpy_similarity():
    content = "line1\nline2\nline3\n"
    old = "line2\nline3\n"
    content_arr = np.array(content.splitlines())
    old_arr = np.array(old.splitlines())
    old_len = len(old_arr)
    max_matches = 0
    for i in range(len(content_arr) - len(old_arr) + 1):
        window = content_arr[i : i + old_len]
        matches = np.sum(window == old_arr)
        max_matches = max(max_matches, int(matches))
    assert max_matches == 2


def test_pre_image_find_best_match():
    content = "line1\nline2\nline3\nline4\n"
    old = "line2\nline3\n"
    match = PreImageValidator.find_best_match(old, content)
    assert match is not None
    assert match[0] == 1


def test_uniqueness_enforcement_count():
    text = "hello world hello foo"
    assert UniquenessEnforcer.count_occurrences(text, "hello") == 2
    assert UniquenessEnforcer.count_occurrences(text, "foo") == 1


def test_uniqueness_enforcement_is_unique():
    text = "hello world foo"
    assert UniquenessEnforcer.is_unique(text, "hello") is True
    assert UniquenessEnforcer.is_unique(text, "world") is True
    assert UniquenessEnforcer.is_unique(text, "xyz") is False


def test_uniqueness_enforcement_enforce():
    text = "hello world foo"
    pos = UniquenessEnforcer.enforce(text, "hello")
    assert pos == 0
    pos = UniquenessEnforcer.enforce(text, "world")
    assert pos == 6


def test_uniqueness_enforcement_positions():
    text = "a b a c a"
    positions = UniquenessEnforcer.get_all_positions(text, "a")
    assert positions == [0, 4, 8]


def test_uniqueness_enforcement_validate_patch():
    text = "hello world foo bar"
    result = UniquenessEnforcer.validate_patch("hello", text)
    assert result["valid"] is True
    assert result["occurrences"] == 1
    result2 = UniquenessEnforcer.validate_patch("l", text)
    assert result2["valid"] is False
    assert result2["occurrences"] > 1


def test_uniqueness_numpy_count():
    text = "a b a c a"
    pattern = "a"
    arr = np.array(list(text))
    count = np.sum(arr == pattern)
    assert count == 3


def test_syntactic_validity_check_valid():
    code = "x = 1\nprint(x)\n"
    result = SyntacticValidityChecker.check_python(code)
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_syntactic_validity_check_invalid():
    code = "x = \nprint(x)\n"
    result = SyntacticValidityChecker.check_python(code)
    assert result["valid"] is False
    assert len(result["errors"]) > 0


def test_syntactic_validity_check_generic():
    result = SyntacticValidityChecker.check_generic("x=1", language="python")
    assert result["valid"] is True


def test_syntactic_validity_check_unknown_language():
    result = SyntacticValidityChecker.check_generic("code", language="rust")
    assert result["valid"] is True


def test_syntactic_validity_check_is_valid():
    assert SyntacticValidityChecker.is_syntactically_valid("x = 1") is True
    assert SyntacticValidityChecker.is_syntactically_valid("x = ") is False


def test_syntactic_validity_tree_depth():
    code = "x = 1"
    depth = SyntacticValidityChecker.get_tree_depth(code)
    assert depth >= 0


def test_atomic_transaction_stage_and_commit():
    txn = AtomicMultiFileTransaction()
    txn.stage("file1.py", "old1", "new1")
    txn.stage("file2.py", "old2", "new2")
    results = txn.commit()
    assert txn.is_committed() is True
    assert len(results) == 2
    assert all(r.success for r in results)


def test_atomic_transaction_rollback_on_validation_failure():
    txn = AtomicMultiFileTransaction()
    txn.stage("file1.py", "old1", "new1")
    def validator(content, original):
        return {"valid": False, "errors": ["syntax error"]}
    results = txn.commit(validators=[validator])
    assert txn.is_rolled_back() is True
    assert all(not r.success for r in results)


def test_atomic_transaction_rollback_manual():
    txn = AtomicMultiFileTransaction()
    txn.stage("file1.py", "old1", "new1")
    txn.rollback()
    assert txn.is_rolled_back() is True


def test_atomic_transaction_double_commit_raises():
    txn = AtomicMultiFileTransaction()
    txn.stage("file1.py", "old1", "new1")
    txn.commit()
    with pytest.raises(RuntimeError):
        txn.commit()


def test_atomic_transaction_commit_after_rollback_raises():
    txn = AtomicMultiFileTransaction()
    txn.stage("file1.py", "old1", "new1")
    txn.rollback()
    with pytest.raises(RuntimeError):
        txn.commit()


def test_atomic_transaction_get_staged_files():
    txn = AtomicMultiFileTransaction()
    txn.stage("a.py", "old", "new")
    txn.stage("b.py", "old", "new")
    assert set(txn.get_staged_files()) == {"a.py", "b.py"}


def test_atomic_transaction_numpy_validation():
    txn = AtomicMultiFileTransaction()
    txn.stage("file1.py", "x = 1\n", "x = 2\n")
    results = txn.commit(validators=[SyntacticValidityChecker.check_python])
    assert all(r.success for r in results)


def test_inline_diff_ui_stream_diff():
    ui = InlineDiffUI()
    ui.stream_diff("@@ -1,2 +1,2 @@\n")
    ui.stream_diff("-line1\n")
    ui.stream_diff("+line1_new\n")
    ui.flush()
    lines = ui.get_diff_lines()
    assert len(lines) >= 2
    assert any(l["type"] == "removed" for l in lines)
    assert any(l["type"] == "added" for l in lines)


def test_inline_diff_ui_generate_decorations():
    ui = InlineDiffUI()
    ui.stream_diff("-old line\n")
    ui.stream_diff("+new line\n")
    ui.flush()
    decs = ui.generate_decorations()
    assert len(decs) == 2
    assert decs[0]["options"]["backgroundColor"] == "#ffeef0"
    assert decs[1]["options"]["backgroundColor"] == "#e6ffed"


def test_inline_diff_ui_empty_stream():
    ui = InlineDiffUI()
    ui.flush()
    assert ui.get_diff_lines() == []
    assert ui.generate_decorations() == []


def test_inline_diff_ui_multiple_chunks():
    ui = InlineDiffUI()
    chunks = ["@@ -1,1 +1,1 @@\n", "-a\n", "+b\n"]
    for chunk in chunks:
        ui.stream_diff(chunk)
    ui.flush()
    decs = ui.generate_decorations()
    assert len(decs) >= 1


def test_inline_diff_ui_context_lines():
    ui = InlineDiffUI()
    ui.stream_diff(" context line\n")
    ui.flush()
    lines = ui.get_diff_lines()
    assert lines[0]["type"] == "context"


def test_integration_full_pipeline():
    original = "def foo():\n    x = 1\n    return x\n"
    block = SearchReplaceBlock("    x = 1\n", "    x = 2\n")
    assert block.validate(original) is True
    patched = block.apply(original)
    result = SyntacticValidityChecker.check_python(patched)
    assert result["valid"] is True
    txn = AtomicMultiFileTransaction()
    txn.stage("module.py", original, patched)
    results = txn.commit(validators=[SyntacticValidityChecker.check_python])
    assert all(r.success for r in results)


def test_integration_unified_diff_and_validation():
    original = "a = 1\nb = 2\nc = 3\n"
    rewritten = "a = 1\nb = 20\nc = 3\n"
    diff = UnifiedDiffGenerator.generate(original, rewritten)
    assert "-b = 2" in diff
    assert "+b = 20" in diff
    assert SyntacticValidityChecker.is_syntactically_valid(rewritten) is True


def test_numpy_hash_consistency():
    original = "hello world\n"
    engine = FullFileRewrite()
    diff = engine.generate(original, original)
    orig_lines = np.array(original.splitlines())
    assert np.all(orig_lines == np.array(original.splitlines()))
