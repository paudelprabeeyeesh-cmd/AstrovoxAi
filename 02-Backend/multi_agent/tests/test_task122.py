import numpy as np
import pytest
from multi_agent.task122_sequential import SequentialOrchestrator


class TestSequentialOrchestrator:
    def test_run_all_pass(self):
        orch = SequentialOrchestrator()
        orch.add_task(lambda: np.array([1, 2, 3]))
        orch.add_task(lambda: np.array([4, 5, 6]))
        results = orch.run()
        assert len(results) == 2
        assert np.array_equal(results[0], np.array([1, 2, 3]))
        assert np.array_equal(results[1], np.array([4, 5, 6]))

    def test_error_propagation(self):
        orch = SequentialOrchestrator()
        orch.add_task(lambda: 1 / 0)
        orch.add_task(lambda: np.array([1, 2]))
        results = orch.run(propagate_errors=True)
        assert results[0] is None
        assert results[1] is None
        assert orch.errors[1] == "Task 0 failed; subsequent task blocked by error propagation."

    def test_no_propagation(self):
        orch = SequentialOrchestrator()
        orch.add_task(lambda: 1 / 0)
        orch.add_task(lambda: np.array([1, 2]))
        results = orch.run(propagate_errors=False)
        assert results[0] is None
        assert np.array_equal(results[1], np.array([1, 2]))
