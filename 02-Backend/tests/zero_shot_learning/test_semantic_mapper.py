from zero_shot_learning.semantic_mapper import SemanticMapper, Concept


def test_add_concept_and_list():
    mapper = SemanticMapper(dim=16)
    c = mapper.add_concept("cat", attributes=["pet", "furry"])
    assert c.name == "cat"
    assert c.attributes == ["pet", "furry"]
    assert "cat" in mapper.list_concepts()


def test_similarity_identical():
    mapper = SemanticMapper(dim=16)
    mapper.add_concept("dog", attributes=["pet", "furry"])
    mapper.add_concept("dog", attributes=["pet", "furry"])
    score = mapper.similarity("dog", "dog")
    assert score > 0.99


def test_similarity_unrelated():
    mapper = SemanticMapper(dim=16)
    mapper.add_concept("cat", attributes=["pet", "furry"])
    mapper.add_concept("car", attributes=["vehicle", "metal"])
    score = mapper.similarity("cat", "car")
    assert score == 0.0


def test_nearest():
    mapper = SemanticMapper(dim=16)
    mapper.add_concept("cat", attributes=["pet", "furry"])
    mapper.add_concept("dog", attributes=["pet", "furry"])
    mapper.add_concept("car", attributes=["vehicle", "metal"])
    results = mapper.nearest("pet animal", k=2)
    assert len(results) == 2
    names = [r[0] for r in results]
    assert "cat" in names or "dog" in names


def test_get_concept():
    mapper = SemanticMapper(dim=8)
    mapper.add_concept("bird")
    concept = mapper.get_concept("bird")
    assert concept is not None
    assert concept.name == "bird"
    assert mapper.get_concept("fish") is None
