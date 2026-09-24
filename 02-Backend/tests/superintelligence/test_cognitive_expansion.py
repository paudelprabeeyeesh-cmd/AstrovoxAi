import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from superintelligence.cognitive_expansion import (
    CognitiveExpander,
    CognitiveResource,
)


class TestCognitiveExpander:
    def test_expand_memory(self):
        expander = CognitiveExpander(initial_memory=100.0)
        result = expander.expand_memory(50.0)
        assert result["added"] == 50.0
        assert expander.memory_capacity == 150.0

    def test_expand_bandwidth(self):
        expander = CognitiveExpander(initial_bandwidth=10.0)
        result = expander.expand_bandwidth(5.0)
        assert result["new_bandwidth"] == 15.0

    def test_allocate_attentional_units(self):
        expander = CognitiveExpander()
        result = expander.allocate_attentional_units(16)
        assert expander.attentional_units == 16
        assert result["units"] == 16

    def test_scale_parallelism(self):
        expander = CognitiveExpander()
        result = expander.scale_parallelism(8)
        assert expander.parallel_threads == 8
        assert result["theoretical_speedup"] > 0.0

    def test_get_cognitive_profile(self):
        expander = CognitiveExpander()
        expander.expand_memory(20.0)
        expander.scale_parallelism(4)
        profile = expander.get_cognitive_profile()
        assert isinstance(profile, CognitiveResource)
        assert profile.memory_capacity == 120.0
        assert profile.parallel_threads == 4

    def test_expansion_stats_keys(self):
        expander = CognitiveExpander()
        expander.expand_memory(10.0)
        stats = expander.get_expansion_stats()
        assert "memory_capacity" in stats
        assert "processing_bandwidth" in stats
        assert stats["total_expansions"] == 1

    def test_expand_memory_clamps_additional(self):
        expander = CognitiveExpander(initial_memory=100.0)
        result = expander.expand_memory(1e12)
        assert result["added"] == 1000.0

    def test_expand_bandwidth_clamps_additional(self):
        expander = CognitiveExpander(initial_bandwidth=10.0)
        result = expander.expand_bandwidth(1e12)
        assert result["added"] == 100.0
