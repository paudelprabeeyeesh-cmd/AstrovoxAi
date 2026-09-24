import pytest
import numpy as np
from agentic_loop.parallel_tool_execution import (
    ParallelToolExecutor,
    DependencyGraph,
    ToolCall,
    ToolResult,
)


def add(a: int, b: int) -> int:
    return a + b


def multiply(a: int, b: int) -> int:
    return a * b


def test_dependency_graph_levels():
    graph = DependencyGraph()
    graph.add_call(ToolCall("a", {}, []))
    graph.add_call(ToolCall("b", {}, ["a"]))
    graph.add_call(ToolCall("c", {}, ["a"]))
    graph.add_call(ToolCall("d", {}, ["b", "c"]))
    levels = graph.get_execution_levels()
    assert levels[0] == ["a"]
    assert set(levels[1]) == {"b", "c"}
    assert levels[2] == ["d"]


def test_dependency_graph_circular_raises():
    graph = DependencyGraph()
    graph.add_call(ToolCall("a", {}, ["b"]))
    graph.add_call(ToolCall("b", {}, ["a"]))
    with pytest.raises(ValueError, match="Circular dependency"):
        graph.get_execution_levels()


def test_parallel_executor_results():
    tools = {"add": add, "multiply": multiply}
    executor = ParallelToolExecutor(tools=tools, max_workers=2)
    calls = [
        ToolCall("add", {"a": 1, "b": 2}, []),
        ToolCall("multiply", {"a": 3, "b": 4}, []),
    ]
    results = executor.execute(calls)
    assert len(results) == 2
    res_map = {r.tool_name: r.result for r in results}
    assert res_map["add"] == 3
    assert res_map["multiply"] == 12
    assert all(r.error is None for r in results)


def test_parallel_executor_unknown_tool():
    tools = {}
    executor = ParallelToolExecutor(tools=tools, max_workers=2)
    calls = [ToolCall("missing", {}, [])]
    results = executor.execute(calls)
    assert results[0].error is not None
    assert "Unknown tool" in results[0].error
