import threading
import time
import numpy as np
import pytest
from multi_agent.task123_parallel import ParallelOrchestrator


class TestParallelOrchestrator:
    def test_run_parallel(self):
        results_list = []

        def task_a():
            time.sleep(0.01)
            return np.array([1, 2])

        def task_b():
            time.sleep(0.01)
            return np.array([3, 4])

        orch = ParallelOrchestrator(max_workers=2)
        orch.add_task(task_a)
        orch.add_task(task_b)
        results = orch.run()
        assert len(results) == 2
        assert np.array_equal(results[0], np.array([1, 2]))
        assert np.array_equal(results[1], np.array([3, 4]))

    def test_sync_point(self):
        orch = ParallelOrchestrator()
        orch.set_sync_point("p1")

        def wait_task():
            return orch.wait_sync_point("p1", timeout=1)

        orch.add_task(wait_task)
        results = orch.run()
        assert results[0] is False

    def test_signal_sync_point(self):
        orch = ParallelOrchestrator()
        orch.set_sync_point("p1")
        orch.signal_sync_point("p1")

        def wait_task():
            return orch.wait_sync_point("p1", timeout=1)

        orch.add_task(wait_task)
        results = orch.run()
        assert results[0] is True

    def test_barrier(self):
        orch = ParallelOrchestrator()
        orch.set_barrier(2)

        def barrier_task():
            return np.array([1])

        orch.add_task(barrier_task)
        orch.add_task(barrier_task)
        results = orch.run()
        assert all(np.array_equal(r, np.array([1])) for r in results)
