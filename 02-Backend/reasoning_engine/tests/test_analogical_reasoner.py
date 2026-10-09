import pytest
from reasoning_engine.analogical_reasoner import AnalogicalReasoner


def test_add_source_fact():
    ar = AnalogicalReasoner()
    ar.add_source_fact("likes", "Alice", "math")
    assert len(ar._source_domain) == 1


def test_add_target_fact():
    ar = AnalogicalReasoner()
    ar.add_target_fact("likes", "Bob", "music")
    assert len(ar._target_domain) == 1


def test_map_relations():
    ar = AnalogicalReasoner()
    ar.add_source_fact("likes", "Alice", "math")
    ar.add_target_fact("likes", "Bob", "music")
    mappings = ar.map_relations()
    assert len(mappings) == 1
    assert mappings[0]["relation"] == "likes"
    assert mappings[0]["confidence"] == 1.0


def test_infer_target():
    ar = AnalogicalReasoner()
    ar.add_source_fact("likes", "Alice", "math")
    ar.add_target_fact("likes", "Bob", "music")
    ar.map_relations()
    inferred = ar.infer_target({"relation": "likes", "subject": "Alice", "object": "math"})
    assert inferred is not None
    assert inferred["subject"] == "Alice"
    assert inferred["object"] == "math"
    assert inferred["confidence"] == 1.0


def test_no_mapping():
    ar = AnalogicalReasoner()
    ar.add_source_fact("likes", "Alice", "math")
    inferred = ar.infer_target({"relation": "likes", "subject": "Alice", "object": "math"})
    assert inferred is None
