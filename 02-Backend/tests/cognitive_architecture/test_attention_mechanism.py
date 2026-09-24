import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from cognitive_architecture.attention_mechanism import (
    AttentionMechanism,
)


class TestAttentionMechanism:
    def test_attend_returns_top_indices(self):
        am = AttentionMechanism(capacity=2)
        items = ["a", "b", "c"]
        priorities = [0.3, 0.9, 0.1]
        attended = am.attend(items, priorities)
        assert attended == [1, 0]
        assert attended[0] == 1

    def test_attend_without_priorities(self):
        am = AttentionMechanism(capacity=3)
        items = ["a", "b"]
        attended = am.attend(items)
        assert len(attended) == 2

    def test_add_item_within_capacity(self):
        am = AttentionMechanism(capacity=3)
        assert am.add_item("a", 0.5, 0.0)
        assert len(am.items) == 1

    def test_capacity_limit(self):
        am = AttentionMechanism(capacity=2)
        am.add_item("a", 0.5, 0.0)
        am.add_item("b", 0.6, 1.0)
        am.add_item("c", 0.7, 2.0)
        assert len(am.items) <= 2

    def test_eviction_removes_lowest(self):
        am = AttentionMechanism(capacity=2)
        am.add_item("low", 0.1, 0.0)
        am.add_item("high", 0.9, 1.0)
        am.add_item("new", 0.5, 2.0)
        contents = [item.content for item in am.items]
        assert "low" not in contents

    def test_get_attended_content(self):
        am = AttentionMechanism(capacity=4)
        am.add_item("a", 1.0, 0.0)
        am.add_item("b", 0.8, 1.0)
        result = am.get_attended_content([0])
        assert result == ["a"]

    def test_get_attended_content_invalid_index(self):
        am = AttentionMechanism(capacity=4)
        am.add_item("a", 1.0, 0.0)
        result = am.get_attended_content([99])
        assert result == []

    def test_step_updates_last_accessed(self):
        am = AttentionMechanism(capacity=4)
        am.add_item("a", 1.0, 0.0)
        initial = am.items[0].last_accessed
        am.step(dt=2.0)
        assert am.items[0].last_accessed == pytest.approx(initial + 2.0)

    def test_capacity_utilization(self):
        am = AttentionMechanism(capacity=4)
        assert am.get_state()["utilization"] == 0.0
        am.add_item("a", 1.0, 0.0)
        assert am.get_state()["utilization"] == pytest.approx(0.25)

    def test_attention_log_records(self):
        am = AttentionMechanism(capacity=4)
        am.attend(["a", "b"], [0.5, 0.9])
        assert len(am.attention_log) == 1
        assert am.attention_log[0]["count"] == 2
