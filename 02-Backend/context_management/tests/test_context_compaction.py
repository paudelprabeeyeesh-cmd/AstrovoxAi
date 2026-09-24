import pytest
import numpy as np
from context_management.context_compaction import ContextCompactor


class TestContextCompactor:
    def test_compact_within_interval(self):
        compactor = ContextCompactor(checkpoint_interval=10)
        turns = [{"role": "user", "content": f"msg {i}"} for i in range(5)]
        result = compactor.compact(turns)
        assert len(result) == 5

    def test_compact_triggers_summary(self):
        compactor = ContextCompactor(checkpoint_interval=4)
        turns = [{"role": "user", "content": f"msg {i}"} for i in range(8)]
        result = compactor.compact(turns)
        assert len(result) < len(turns)

    def test_add_turn_creates_checkpoint(self):
        compactor = ContextCompactor(checkpoint_interval=3)
        for i in range(6):
            compactor.add_turn({"role": "user", "content": f"msg {i}"})
        assert compactor.get_checkpoint_count() == 2

    def test_invalid_checkpoint_interval(self):
        with pytest.raises(ValueError):
            ContextCompactor(checkpoint_interval=0)

    def test_invalid_max_context_tokens(self):
        with pytest.raises(ValueError):
            ContextCompactor(checkpoint_interval=10, max_context_tokens=0)

    def test_checkpoint_has_turn_number(self):
        compactor = ContextCompactor(checkpoint_interval=5)
        for i in range(10):
            compactor.add_turn({"role": "user", "content": f"msg {i}"})
        checkpoints = compactor.checkpoints
        assert checkpoints[0]["turn"] == 5
        assert checkpoints[1]["turn"] == 10

    def test_checkpoint_summary_non_empty(self):
        compactor = ContextCompactor(checkpoint_interval=3, max_context_tokens=100)
        for i in range(6):
            compactor.add_turn({"role": "user", "content": f"message {i} with some words"})
        for cp in compactor.checkpoints:
            assert len(cp["summary"]) > 0

    def test_numpy_compaction_ratio(self):
        np.random.seed(3)
        for _ in range(20):
            interval = int(np.random.randint(3, 10))
            compactor = ContextCompactor(checkpoint_interval=interval)
            num_turns = int(np.random.randint(interval + 1, 30))
            turns = [{"role": "user", "content": f"msg {i}"} for i in range(num_turns)]
            result = compactor.compact(turns)
            assert len(result) <= num_turns
            assert len(result) >= 1

    def test_zero_add_turns(self):
        compactor = ContextCompactor(checkpoint_interval=5)
        assert compactor.get_checkpoint_count() == 0

    def test_exact_interval_multiple(self):
        compactor = ContextCompactor(checkpoint_interval=4)
        for i in range(8):
            compactor.add_turn({"role": "user", "content": f"msg {i}"})
        assert compactor.get_checkpoint_count() == 2
