import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from superintelligence.collective_superintelligence import (
    CollectiveSuperintelligence,
    CollectiveNode,
)


class TestCollectiveSuperintelligence:
    def test_add_node(self):
        cs = CollectiveSuperintelligence(node_embedding_dim=16)
        node = cs.add_node("node1", capability=0.8, specialization="reasoning")
        assert isinstance(node, CollectiveNode)
        assert node.id == "node1"
        assert node.specialization == "reasoning"

    def test_amplify_collective_empty(self):
        cs = CollectiveSuperintelligence()
        state = cs.amplify_collective()
        assert state.active_nodes == 0
        assert state.total_capability == 0.0

    def test_amplify_collective_with_nodes(self):
        cs = CollectiveSuperintelligence(node_embedding_dim=16)
        cs.add_node("n1", 0.5, "reasoning")
        cs.add_node("n2", 0.7, "planning")
        state = cs.amplify_collective(interaction_strength=0.3)
        assert state.active_nodes == 2
        assert state.total_capability == pytest.approx(1.2)

    def test_emergent_consensus_empty(self):
        cs = CollectiveSuperintelligence()
        result = cs.emergent_consensus(np.random.randn(16), threshold=0.8)
        assert result["consensus_reached"] is False

    def test_emergent_consensus_with_nodes(self):
        cs = CollectiveSuperintelligence(node_embedding_dim=16)
        cs.add_node("n1", 0.5, "reasoning")
        cs.add_node("n2", 0.7, "planning")
        topic = np.random.randn(16)
        result = cs.emergent_consensus(topic, threshold=-1.0)
        assert "aligned_nodes" in result
        assert "alignment_scores" in result

    def test_collective_stats(self):
        cs = CollectiveSuperintelligence(node_embedding_dim=16)
        cs.add_node("n1", 0.5, "reasoning")
        cs.amplify_collective()
        stats = cs.get_collective_stats()
        assert stats["nodes"] == 1
        assert stats["states_recorded"] == 1
