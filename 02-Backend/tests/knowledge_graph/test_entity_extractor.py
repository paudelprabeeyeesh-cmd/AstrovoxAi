import pytest
from knowledge_graph.entity_extractor import EntityExtractor, EntityMatch


class TestEntityExtractor:
    def test_extract_persons(self):
        extractor = EntityExtractor()
        text = "Alice and Bob went to the store."
        matches = extractor.extract(text)
        persons = [m for m in matches if m.entity_type == "person"]
        assert len(persons) == 2
        assert persons[0].text == "Alice"
        assert persons[1].text == "Bob"

    def test_extract_dates(self):
        extractor = EntityExtractor()
        text = "The event is on 2024-01-15 and 2025-12-31."
        matches = extractor.extract(text)
        dates = [m for m in matches if m.entity_type == "date"]
        assert len(dates) == 2
        assert dates[0].text == "2024-01-15"

    def test_extract_by_type(self):
        extractor = EntityExtractor()
        text = "In 2020-01-01 we saw numbers like 42 and 3.14."
        dates = extractor.extract_types(text, "date")
        assert len(dates) == 1

    def test_add_pattern(self):
        extractor = EntityExtractor()
        extractor.add_pattern("email", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
        matches = extractor.extract("Contact test@example.com for help.")
        emails = [m for m in matches if m.entity_type == "email"]
        assert len(emails) == 1
        assert emails[0].text == "test@example.com"

    def test_supported_types(self):
        extractor = EntityExtractor()
        assert "person" in extractor.supported_types()
        assert "date" in extractor.supported_types()

    def test_empty_text(self):
        extractor = EntityExtractor()
        assert extractor.extract("") == []
