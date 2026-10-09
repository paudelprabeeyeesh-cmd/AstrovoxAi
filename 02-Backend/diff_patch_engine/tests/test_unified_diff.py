from diff_patch_engine.unified_diff import UnifiedDiffGenerator


def test_unified_diff_generate_adds_hunks():
    original = "line1\nline2\nline3\n"
    rewritten = "line1\nline2_modified\nline3_extra\n"
    diff = UnifiedDiffGenerator.generate(original, rewritten)
    assert "@@" in diff
    assert "-line2" in diff
    assert "+line2_modified" in diff
    assert "+line3_extra" in diff


def test_unified_diff_generate_no_changes():
    original = "line1\nline2\n"
    diff = UnifiedDiffGenerator.generate(original, original)
    assert "@@" not in diff


def test_unified_diff_generate_multiple_hunks():
    original = "a\nb\nc\nd\ne\n"
    rewritten = "a\nb2\nc\nd2\ne\n"
    diff = UnifiedDiffGenerator.generate(original, rewritten)
    assert "-b\n" in diff
    assert "+b2\n" in diff
    assert "-d\n" in diff
    assert "+d2\n" in diff


def test_unified_diff_generate_empty_original():
    original = ""
    rewritten = "hello\n"
    diff = UnifiedDiffGenerator.generate(original, rewritten)
    assert "+hello" in diff


def test_unified_diff_generate_adds_line():
    original = "line1\nline2\n"
    rewritten = "line1\nline1_5\nline2\n"
    diff = UnifiedDiffGenerator.generate(original, rewritten)
    assert "+line1_5" in diff


def test_unified_diff_parse_single_hunk():
    diff_text = "--- original\n+++ rewritten\n@@ -2,1 +2,2 @@\n-line2\n+line2_modified\n+line3_extra\n"
    hunks = UnifiedDiffGenerator.parse(diff_text)
    assert len(hunks) == 1
    assert hunks[0][0] == 2
    assert hunks[0][1] == 1
    assert hunks[0][2] == 2
    assert hunks[0][3] == 2


def test_unified_diff_parse_no_hunks():
    diff_text = "--- original\n+++ rewritten\n"
    hunks = UnifiedDiffGenerator.parse(diff_text)
    assert hunks == []
