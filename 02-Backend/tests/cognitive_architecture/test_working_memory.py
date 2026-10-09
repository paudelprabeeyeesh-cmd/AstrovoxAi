import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from cognitive_architecture.working_memory import (
    WorkingMemoryBuffer,
    AttentionGate,
    WorkingMemorySystem,
    MemoryChunk,
)


class TestMemoryChunk:
    def test_activation_decays(self):
        chunk = MemoryChunk(content="test", salience=1.0, timestamp=0.0, decay_rate=0.1)
        chunk.age = 1.0
        assert chunk.get_activation() == pytest.approx(np.exp(-0.1))

    def test_no_decay_when_zero_age(self):
        chunk = MemoryChunk(content="test", salience=0.8, timestamp=0.0)
        assert chunk.get_activation() == pytest.approx(0.8)


class TestWorkingMemoryBuffer:
    def test_add_within_capacity(self):
        buf = WorkingMemoryBuffer(capacity=4)
        assert buf.add("a", 1.0, 0.0)
        assert buf.add("b", 0.8, 1.0)
        assert len(buf.chunks) == 2

    def test_capacity_limit(self):
        buf = WorkingMemoryBuffer(capacity=2)
        buf.add("a", 1.0, 0.0)
        buf.add("b", 1.0, 1.0)
        buf.add("c", 1.0, 2.0)
        assert len(buf.chunks) <= 2

    def test_eviction_removes_lowest(self):
        buf = WorkingMemoryBuffer(capacity=2)
        buf.add("high", 1.0, 0.0)
        buf.add("low", 0.1, 1.0)
        buf.add("new", 1.0, 2.0)
        contents = [c.content for c in buf.chunks]
        assert "low" not in contents

    def test_attend_returns_contents(self):
        buf = WorkingMemoryBuffer(capacity=4)
        buf.add("a", 1.0, 0.0)
        buf.add("b", 1.0, 1.0)
        result = buf.attend([0])
        assert result == ["a"]

    def test_attend_invalid_index_ignored(self):
        buf = WorkingMemoryBuffer(capacity=4)
        buf.add("a", 1.0, 0.0)
        result = buf.attend([99])
        assert result == []

    def test_step_increments_age(self):
        buf = WorkingMemoryBuffer(capacity=4)
        buf.add("a", 1.0, 0.0)
        initial_age = buf.chunks[0].age
        buf.step(dt=2.0)
        assert buf.chunks[0].age == pytest.approx(initial_age + 2.0)

    def test_capacity_utilization(self):
        buf = WorkingMemoryBuffer(capacity=4)
        assert buf.capacity_utilization() == 0.0
        buf.add("a", 1.0, 0.0)
        assert buf.capacity_utilization() == pytest.approx(0.25)


class TestAttentionGate:
    def test_no_goal_allows_all(self):
        gate = AttentionGate(threshold=0.5)
        items = ["a", "b", "c"]
        vectors = np.random.randn(3, 4)
        passed = gate.gate(items, vectors)
        assert len(passed) == 3

    def test_goal_filters_by_similarity(self):
        gate = AttentionGate(threshold=0.3, top_down_weight=1.0)
        goal = np.array([1.0, 0.0, 0.0, 0.0])
        gate.set_goal(goal)
        items = ["x", "y", "z"]
        vectors = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.5, 0.5, 0.0, 0.0],
        ])
        passed = gate.gate(items, vectors)
        assert 0 in passed
        assert 1 not in passed

    def test_attention_allocation(self):
        gate = AttentionGate(threshold=0.3, top_down_weight=1.0)
        gate.set_goal(np.array([1.0, 0.0]))
        items = ["x"]
        vectors = np.array([[1.0, 0.0]])
        alloc = gate.get_attention_allocation(items, vectors)
        assert 0 in alloc
        assert alloc[0] == pytest.approx(1.0)


class TestWorkingMemorySystem:
    def test_register_item(self):
        wm = WorkingMemorySystem(capacity=4)
        idx = wm.register_item("test", np.array([1.0, 0.0]))
        assert idx == 0

    def test_process_input_accepted(self):
        wm = WorkingMemorySystem(capacity=4)
        accepted = wm.process_input("item", np.array([1.0, 0.0]), salience=0.9, timestamp=0.0)
        assert accepted

    def test_process_input_rejected_by_gate(self):
        wm = WorkingMemorySystem(capacity=4)
        wm.gate.threshold = 0.99
        wm.gate.set_goal(np.array([1.0, 0.0]))
        accepted = wm.process_input("item", np.array([0.0, 1.0]), salience=0.1, timestamp=0.0)
        assert not accepted

    def test_step_ages_chunks(self):
        wm = WorkingMemorySystem(capacity=4)
        wm.process_input("item", np.array([1.0, 0.0]), salience=1.0, timestamp=0.0)
        wm.step(dt=1.0)
        assert wm.buffer.chunks[0].age > 0

    def test_get_state(self):
        wm = WorkingMemorySystem(capacity=4)
        wm.process_input("a", np.array([1.0, 0.0]), salience=1.0, timestamp=0.0)
        state = wm.get_state()
        assert "contents" in state
        assert "activations" in state
