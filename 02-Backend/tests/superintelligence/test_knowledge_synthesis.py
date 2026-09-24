import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from superintelligence.knowledge_synthesis import (
    KnowledgeSynthesizer,
    KnowledgeNode,
)


class TestKnowledgeSynthesizer:
    def test_add_knowledge(self):
        synth = KnowledgeSynthesizer(embedding_dim=32)
        node = synth.add_knowledge("n1", "physics", np.random.randn(32), confidence=0.9)
        assert isinstance(node, KnowledgeNode)
        assert node.id == "n1"
        assert node.domain == "physics"

    def test_synthesize_weighted_average(self):
        synth = KnowledgeSynthesizer(embedding_dim=32)
        synth.add_knowledge("n1", "math", np.random.randn(32), confidence=0.8)
        synth.add_knowledge("n2", "cs", np.random.randn(32), confidence=0.9)
        result = synth.synthesize(["n1", "n2"], synthesis_method="weighted_average")
        assert "synthesized_embedding" in result
        assert len(result["synthesized_embedding"]) == 32
        assert result["mean_confidence"] == pytest.approx(0.85)

    def test_synthesize_requires_two_nodes(self):
        synth = KnowledgeSynthesizer(embedding_dim=32)
        synth.add_knowledge("n1", "math", np.random.randn(32))
        with pytest.raises(ValueError):
            synth.synthesize(["n1"])

    def test_find_analogies(self):
        synth = KnowledgeSynthesizer(embedding_dim=32)
        synth.add_knowledge("n1", "math", np.random.randn(32))
        synth.add_knowledge("n2", "cs", np.random.randn(32))
        synth.add_knowledge("n3", "physics", np.random.randn(32))
        analogies = synth.find_analogies("n1", "n2", top_k=2)
        assert len(analogies) <= 2
        assert all(isinstance(a, tuple) for a in analogies)

    def test_knowledge_stats(self):
        synth = KnowledgeSynthesizer(embedding_dim=32)
        synth.add_knowledge("n1", "math", np.random.randn(32))
        synth.add_knowledge("n2", "cs", np.random.randn(32))
        stats = synth.get_knowledge_stats()
        assert stats["node_count"] == 2
        assert "math" in stats["domains"]
