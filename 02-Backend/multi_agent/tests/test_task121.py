import numpy as np
import pytest
from multi_agent.task121_agents import MainAgent, SubAgent, SubTask


class DummyAgent(SubAgent):
    def execute(self, task: SubTask) -> int:
        return len(task.compressed_context) if task.compressed_context is not None else 0


class TestMainAgent:
    def test_register_and_delegate(self):
        agent = MainAgent()
        sub = DummyAgent("worker")
        agent.register_sub_agent(sub)
        agent.set_context_vector(np.arange(64, dtype=float))
        task = SubTask(name="worker", payload={}, context_budget=8)
        result = agent.delegate(task)
        assert result == 8
        assert task.compressed_context.size == 8

    def test_context_compression(self):
        agent = MainAgent()
        ctx = np.arange(32, dtype=float)
        compressed = agent.compress_context(ctx, 10)
        assert compressed.size == 10

    def test_delegate_missing_agent(self):
        agent = MainAgent()
        agent.set_context_vector(np.arange(4, dtype=float))
        task = SubTask(name="ghost", payload={}, context_budget=4)
        with pytest.raises(ValueError):
            agent.delegate(task)

    def test_delegate_without_context_vector(self):
        agent = MainAgent()
        sub = DummyAgent("worker")
        agent.register_sub_agent(sub)
        task = SubTask(name="worker", payload={}, context_budget=4)
        with pytest.raises(RuntimeError):
            agent.delegate(task)

    def test_batch_delegate(self):
        agent = MainAgent()
        for name in ["a", "b"]:
            agent.register_sub_agent(DummyAgent(name))
        agent.set_context_vector(np.arange(32, dtype=float))
        tasks = [
            SubTask(name="a", payload={}, context_budget=4),
            SubTask(name="b", payload={}, context_budget=4),
        ]
        results = agent.delegate_batch(tasks)
        assert results == [4, 4]
