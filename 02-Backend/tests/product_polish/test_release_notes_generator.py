
from product_polish.release_notes_generator import ReleaseNotesGenerator


def test_add_and_list_entries():
    generator = ReleaseNotesGenerator()
    entry = generator.add_entry("1.0.0", "New Dashboard", "Added dashboard view.", author="alice")
    assert entry.version == "1.0.0"
    assert entry.entry_type == "feature"
    assert entry.author == "alice"

    entries = generator.list_entries(version="1.0.0")
    assert len(entries) == 1
    assert entries[0].id == entry.id


def test_parse_commit_message():
    generator = ReleaseNotesGenerator()
    message = "feat(auth): add OAuth login\nfix: resolve crash on startup\nperf: improve load time"
    entries = generator.parse_commit_message("2.0.0", message, author="bob")
    assert len(entries) == 3
    assert entries[0].entry_type == "feature"
    assert entries[1].entry_type == "bugfix"
    assert entries[2].entry_type == "improvement"
    assert entries[0].source == "commit"
    assert entries[0].author == "bob"


def test_generate_notes_grouped():
    generator = ReleaseNotesGenerator()
    generator.add_entry("1.0.0", "Fix A", "Fixed A.", entry_type="bugfix")
    generator.add_entry("1.0.0", "Feature X", "Added X.", entry_type="feature")

    notes = generator.generate_notes("1.0.0", group_by_type=True)
    assert "# Release Notes 1.0.0" in notes
    assert "## Feature" in notes
    assert "## Bugfix" in notes


def test_generate_notes_ungrouped():
    generator = ReleaseNotesGenerator()
    generator.add_entry("1.0.0", "Fix A", "Fixed A.", entry_type="bugfix")
    generator.add_entry("1.0.0", "Feature X", "Added X.", entry_type="feature")

    notes = generator.generate_notes("1.0.0", group_by_type=False)
    assert "## " not in notes
    assert "- [feature] Feature X: Added X." in notes
    assert "- [bugfix] Fix A: Fixed A." in notes


def test_entry_type_normalization():
    generator = ReleaseNotesGenerator()
    entry = generator.add_entry("1.0.0", "Docs", "Updated README.", entry_type="docs")
    assert entry.entry_type == "documentation"
    assert entry.raw_type == "docs"
