import pytest

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from superintelligence.abstraction_engine import (
    AbstractionEngine,
    Pattern,
    AbstractionHierarchy,
)


class TestAbstractionEngine:
    def test_register_pattern(self):
        engine = AbstractionEngine(max_hierarchy_depth=5, min_confidence=0.5)
        pattern = engine.register_pattern("alpha", ["s1", "s2"], abstraction_level=1, confidence=0.8)
        assert isinstance(pattern, Pattern)
        assert pattern.name == "alpha"
        assert len(pattern.source_descriptions) == 2

    def test_register_pattern_low_confidence_raises(self):
        engine = AbstractionEngine(max_hierarchy_depth=5, min_confidence=0.7)
        with pytest.raises(ValueError):
            engine.register_pattern("beta", ["s1"], confidence=0.3)

    def test_extract_patterns(self):
        engine = AbstractionEngine(max_hierarchy_depth=5)
        descriptions = ["alpha beta", "alpha gamma", "alpha delta"]
        patterns = engine.extract_patterns(descriptions, min_sources=2)
        assert len(patterns) > 0

    def test_build_hierarchy(self):
        engine = AbstractionEngine(max_hierarchy_depth=5)
        pattern = engine.register_pattern("root", ["src"], abstraction_level=0, confidence=0.9)
        hierarchy = engine.build_hierarchy(pattern)
        assert isinstance(hierarchy, AbstractionHierarchy)
        assert len(hierarchy.layers) >= 1

    def test_generalize(self):
        engine = AbstractionEngine(max_hierarchy_depth=5)
        pattern = engine.register_pattern("root", ["src1", "src2"], abstraction_level=0, confidence=0.9)
        hierarchy = engine.build_hierarchy(pattern)
        general = engine.generalize(hierarchy)
        assert general.name.endswith("__general")

    def test_get_patterns_by_level(self):
        engine = AbstractionEngine(max_hierarchy_depth=5)
        engine.register_pattern("p1", ["s1"], abstraction_level=0, confidence=0.8)
        engine.register_pattern("p2", ["s2"], abstraction_level=1, confidence=0.8)
        engine.register_pattern("p3", ["s3"], abstraction_level=2, confidence=0.8)
        level_0 = engine.get_patterns_by_level(0)
        assert len(level_0) == 1
        assert level_0[0].name == "p1"

    def test_list_patterns(self):
        engine = AbstractionEngine(max_hierarchy_depth=5)
        engine.register_pattern("p1", ["s1"], abstraction_level=0, confidence=0.9)
        filtered = engine.list_patterns(min_confidence=0.5)
        assert len(filtered) == 1
        assert filtered[0].name == "p1"

    def test_stats(self):
        engine = AbstractionEngine(max_hierarchy_depth=5)
        engine.register_pattern("p1", ["s1"], abstraction_level=0, confidence=0.9)
        engine.register_pattern("p2", ["s2"], abstraction_level=1, confidence=0.8)
        stats = engine.get_stats()
        assert stats["total_patterns"] == 2
        assert stats["total_hierarchies"] == 0

    def test_register_pattern_clamps_level(self):
        engine = AbstractionEngine(max_hierarchy_depth=3)
        pattern = engine.register_pattern("p", ["s"], abstraction_level=10)
        assert pattern.abstraction_level == 3

    def test_build_hierarchy_empty_layers_raises(self):
        engine = AbstractionEngine(max_hierarchy_depth=5)
        empty_hierarchy = AbstractionHierarchy(id="h1", root_pattern="root", layers=[], compression_ratio=0.0)
        with pytest.raises(ValueError):
            engine.generalize(empty_hierarchy)

    def test_list_patterns_max_level(self):
        engine = AbstractionEngine(max_hierarchy_depth=5)
        engine.register_pattern("p1", ["s1"], abstraction_level=0, confidence=0.9)
        engine.register_pattern("p2", ["s2"], abstraction_level=2, confidence=0.8)
        filtered = engine.list_patterns(min_confidence=0.0, max_level=1)
        assert len(filtered) == 1

    def test_derive_name_empty_descriptions(self):
        engine = AbstractionEngine(max_hierarchy_depth=5)
        name = engine._derive_name([])
        assert name == "pattern"

    def test_decompose_long_description(self):
        engine = AbstractionEngine(max_hierarchy_depth=5)
        parts = engine._decompose("hello world foo bar baz")
        assert len(parts) == 3
        assert parts[0] == "hello_world"
