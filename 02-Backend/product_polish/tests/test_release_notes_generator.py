"""
Tests for product_polish.release_notes_generator

Uses only stdlib.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from product_polish.release_notes_generator import ReleaseNotesGenerator  # noqa: E402


@pytest.fixture()
def generator():
    return ReleaseNotesGenerator()


class TestReleaseNotesGeneratorAddEntry:
    def test_add_returns_entry(self, generator):
        entry = generator.add_entry("1.0.0", "Initial Release", "First public release")
        from product_polish.release_notes_generator import ReleaseNoteEntry
        assert isinstance(entry, ReleaseNoteEntry)

    def test_add_assigns_id(self, generator):
        entry = generator.add_entry("1.0.0", "Feature", "Added X")
        assert entry.id != ""

    def test_add_normalizes_type(self, generator):
        entry = generator.add_entry("1.0.0", "Fix", "Fixed Y", entry_type="fix")
        assert entry.entry_type == "bugfix"

    def test_add_sets_created_at(self, generator):
        entry = generator.add_entry("1.0.0", "Feature", "Added X")
        assert "T" in entry.created_at

    def test_add_stores_entry(self, generator):
        entry = generator.add_entry("1.0.0", "Feature", "Added X")
        got = generator.get_entry(entry.id)
        assert got is not None
        assert got.title == "Feature"

    def test_add_default_source_manual(self, generator):
        entry = generator.add_entry("1.0.0", "Feature", "Added X")
        assert entry.source == "manual"

    def test_add_custom_source(self, generator):
        entry = generator.add_entry("1.0.0", "Feature", "Added X", source="commit")
        assert entry.source == "commit"


class TestReleaseNotesGeneratorGetEntry:
    def test_get_missing_returns_none(self, generator):
        assert generator.get_entry("nonexistent") is None


class TestReleaseNotesGeneratorListEntries:
    def test_list_empty(self, generator):
        assert generator.list_entries() == []

    def test_list_after_add(self, generator):
        generator.add_entry("1.0.0", "Feature A", "Added A")
        generator.add_entry("1.0.0", "Feature B", "Added B")
        assert len(generator.list_entries()) == 2

    def test_list_filter_by_version(self, generator):
        generator.add_entry("1.0.0", "A", "Added A")
        generator.add_entry("2.0.0", "B", "Added B")
        items = generator.list_entries(version="1.0.0")
        assert len(items) == 1
        assert items[0].version == "1.0.0"

    def test_list_sorted_by_version_then_date(self, generator):
        generator.add_entry("2.0.0", "B", "B desc")
        generator.add_entry("1.0.0", "A", "A desc")
        items = generator.list_entries()
        assert items[0].version == "1.0.0"
        assert items[1].version == "2.0.0"


class TestReleaseNotesGeneratorParseCommit:
    def test_parse_simple(self, generator):
        entries = generator.parse_commit_message("1.0.0", "feat: add login\nfix: resolve crash")
        assert len(entries) == 2
        assert entries[0].entry_type == "feature"
        assert entries[1].entry_type == "bugfix"

    def test_parse_with_scope(self, generator):
        entries = generator.parse_commit_message("1.0.0", "feat(api): add users endpoint")
        assert len(entries) == 1
        assert "(api)" in entries[0].title

    def test_parse_unknown_type_defaults_to_feature(self, generator):
        entries = generator.parse_commit_message("1.0.0", "chore: clean imports")
        assert entries[0].entry_type == "maintenance"

    def test_parse_empty_message(self, generator):
        entries = generator.parse_commit_message("1.0.0", "")
        assert entries == []


class TestReleaseNotesGeneratorGenerateNotes:
    def test_generate_empty_version(self, generator):
        notes = generator.generate_notes("1.0.0")
        assert "No entries" in notes

    def test_generate_contains_version(self, generator):
        generator.add_entry("1.0.0", "Feature", "Added X")
        notes = generator.generate_notes("1.0.0")
        assert "1.0.0" in notes

    def test_generate_grouped_by_type(self, generator):
        generator.add_entry("1.0.0", "Fix", "Fixed X", entry_type="fix")
        generator.add_entry("1.0.0", "Feat", "Added Y", entry_type="feat")
        notes = generator.generate_notes("1.0.0", group_by_type=True)
        assert "## Bugfix" in notes
        assert "## Feature" in notes

    def test_generate_flat(self, generator):
        generator.add_entry("1.0.0", "Fix", "Fixed X", entry_type="fix")
        generator.add_entry("1.0.0", "Feat", "Added Y", entry_type="feat")
        notes = generator.generate_notes("1.0.0", group_by_type=False)
        assert "## " not in notes
        assert "[fix]" in notes
        assert "[feature]" in notes
