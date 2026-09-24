import pytest
from multi_agent.task126_deadlock import WaitForGraph


class TestWaitForGraph:
    def test_no_deadlock_in_dag(self):
        g = WaitForGraph()
        g.add_wait("A", "B")
        g.add_wait("B", "C")
        assert g.detect_deadlock() is False
        assert g.has_cycle is False
        assert g.cycle is None

    def test_simple_cycle_dorrect_nodes(self):
        g = WaitForGraph()
        g.add_wait("A", "B")
        g.add_wait("B", "A")
        assert g.detect_deadlock() is True
        assert g.has_cycle is True
        assert g.cycle is not None
        assert len(g.cycle) >= 2
        assert g.cycle[0] == g.cycle[-1]
        assert set(g.cycle[:-1]) == {"A", "B"}

    def test_three_node_cycle(self):
        g = WaitForGraph()
        g.add_wait("X", "Y")
        g.add_wait("Y", "Z")
        g.add_wait("Z", "X")
        assert g.detect_deadlock() is True
        assert g.has_cycle is True
        assert g.cycle is not None
        assert g.cycle[0] == g.cycle[-1]
        assert set(g.cycle[:-1]) == {"X", "Y", "Z"}

    def test_self_wait_cycle(self):
        g = WaitForGraph()
        g.add_wait("A", "A")
        assert g.detect_deadlock() is True
        assert g.cycle == ["A", "A"]

    def test_empty_graph(self):
        g = WaitForGraph()
        assert g.detect_deadlock() is False

    def test_isolated_nodes(self):
        g = WaitForGraph()
        g.add_wait("A", "B")
        g.add_wait("X", "Y")
        assert g.detect_deadlock() is False
