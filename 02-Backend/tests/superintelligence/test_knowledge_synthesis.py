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

    def test_add_knowledge_pads_embedding(self):
        synth = KnowledgeSynthesizer(embedding_dim=32)
        node = synth.add_knowledge("n1", "math", np.random.randn(16))
        assert node.embedding.shape == (32,)

    def test_synthesize_requires_valid_nodes(self):
        synth = KnowledgeSynthesizer(embedding_dim=32)
        synth.add_knowledge("n1", "math", np.random.randn(32))
        with pytest.raises(ValueError):
            synth.synthesize(["n1", "invalid"])

    def test_synthesize_cross_domain_blend(self):
        synth = KnowledgeSynthesizer(embedding_dim=32)
        synth.add_knowledge("n1", "math", np.random.randn(32))
        synth.add_knowledge("n2", "cs", np.random.randn(32))
        result = synth.synthesize(["n1", "n2"], synthesis_method="cross_domain_blend")
        assert len(result["synthesized_embedding"]) == 32

    def test_synthesize_concatenate(self):
        synth = KnowledgeSynthesizer(embedding_dim=32)
        synth.add_knowledge("n1", "math", np.random.randn(32))
        synth.add_knowledge("n2", "cs", np.random.randn(32))
        result = synth.synthesize(["n1", "n2"], synthesis_method="concatenate")
        assert len(result["synthesized_embedding"]) == 64

    def test_find_analogies_missing_nodes(self):
        synth = KnowledgeSynthesizer(embedding_dim=32)
        synth.add_knowledge("n1", "math", np.random.randn(32))
        analogies = synth.find_analogies("missing", "n1")
        assert analogies == []

    def test_knowledge_stats_empty(self):
        synth = KnowledgeSynthesizer(embedding_dim=32)
        stats = synth.get_knowledge_stats()
        assert stats["node_count"] == 0
