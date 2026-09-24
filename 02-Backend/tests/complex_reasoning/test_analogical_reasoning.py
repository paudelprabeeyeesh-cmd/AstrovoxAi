import pytest
import numpy as np
from complex_reasoning.analogical_reasoning import Attribute, Relation, Concept, StructureMapping, AnalogyEngine


class TestAttribute:
    def test_distance(self):
        a = Attribute("size", 1.0)
        b = Attribute("size", 4.0)
        assert a.distance_to(b) == pytest.approx(3.0)


class TestConcept:
    def test_similarity(self):
        c1 = Concept("A", attributes=[Attribute("x", 1.0), Attribute("y", 2.0)])
        c2 = Concept("B", attributes=[Attribute("x", 1.0), Attribute("y", 2.0)])
        assert c1.similarity_to(c2) == pytest.approx(1.0)

    def test_similarity_no_common(self):
        c1 = Concept("A", attributes=[Attribute("x", 1.0)])
        c2 = Concept("B", attributes=[Attribute("y", 2.0)])
        assert c1.similarity_to(c2) == pytest.approx(0.0)


class TestStructureMapping:
    def test_compute_mapping(self):
        s = Concept("S", attributes=[Attribute("a", 1.0)], relations=[Relation("S", "T", "link")])
        t = Concept("T", attributes=[Attribute("a", 1.0)], relations=[Relation("S", "T", "link")])
        sm = StructureMapping(s, t)
        score = sm.compute_mapping()
        assert score > 0.0

    def test_find_best_analogy(self):
        s = Concept("S", attributes=[Attribute("a", 1.0)])
        t1 = Concept("T1", attributes=[Attribute("a", 1.0)])
        t2 = Concept("T2", attributes=[Attribute("a", 2.0)])
        sm = StructureMapping(s, t1)
        best, score = sm.find_best_analogy([t1, t2])
        assert best.name == "T1"


class TestAnalogyEngine:
    def test_add_concept(self):
        engine = AnalogyEngine()
        engine.add_concept(Concept("A"), is_prior=False)
        assert len(engine.domain) == 1

    def test_domain_analysis(self):
        engine = AnalogyEngine()
        engine.add_concept(Concept("A", attributes=[Attribute("x", 1.0)]))
        engine.add_concept(Concept("B", attributes=[Attribute("x", 2.0)]))
        stats = engine.domain_analysis()
        assert "x" in stats
        assert stats["x"] == pytest.approx(1.0)

    def test_search(self):
        engine = AnalogyEngine()
        s = Concept("S", attributes=[Attribute("a", 1.0)], relations=[Relation("S", "T", "r")])
        t = Concept("T", attributes=[Attribute("a", 1.0)], relations=[Relation("S", "T", "r")])
        engine.add_concept(s)
        engine.add_concept(t)
        results = engine.search(s)
        assert len(results) == 1
        assert results[0][0].name == "T"

    def test_inference(self):
        s = Concept("S", relations=[Relation("S", "T", "cause")])
        t = Concept("T", relations=[Relation("T", "U", "cause")])
        engine = AnalogyEngine()
        inferred = engine.inference(s, t)
        assert len(inferred) == 1
        assert inferred[0].source == "T"
        assert inferred[0].target == "U"
