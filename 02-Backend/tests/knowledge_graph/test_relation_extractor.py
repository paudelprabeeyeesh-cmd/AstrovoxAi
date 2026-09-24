import pytest
from knowledge_graph.relation_extractor import RelationExtractor, RelationMatch


class TestRelationExtractor:
    def test_extract_works_for(self):
        extractor = RelationExtractor()
        text = "Alice works for Acme Corp."
        matches = extractor.extract(text)
        assert len(matches) == 1
        assert matches[0].subject == "Alice"
        assert matches[0].object == "Acme"
        assert matches[0].predicate == "works_for"

    def test_extract_located_in(self):
        extractor = RelationExtractor()
        text = "Paris is in France."
        matches = extractor.extract(text)
        assert len(matches) == 1
        assert matches[0].subject == "Paris"
        assert matches[0].object == "France"
        assert matches[0].predicate == "located_in"

    def test_extract_by_type(self):
        extractor = RelationExtractor()
        text = "Bob was born in London."
        matches = extractor.extract_by_type(text, "born_in")
        assert len(matches) == 1
        assert matches[0].subject == "Bob"
        assert matches[0].object == "London"

    def test_no_match(self):
        extractor = RelationExtractor()
        assert extractor.extract("Hello world.") == []

    def test_case_insensitive(self):
        extractor = RelationExtractor()
        text = "ALICE WORKS FOR ACME CORP."
        matches = extractor.extract(text)
        assert len(matches) == 1

    def test_add_template(self):
        extractor = RelationExtractor()
        extractor.add_template("owns", r"(?P<subject>\w+)\s+owns\s+(?P<object>\w+)")
        matches = extractor.extract("Alice owns Bob.")
        assert len(matches) == 1
        assert matches[0].predicate == "owns"

    def test_supported_predicates(self):
        extractor = RelationExtractor()
        assert "works_for" in extractor.supported_predicates()
