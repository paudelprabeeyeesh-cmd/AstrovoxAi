from agentic_loop.react_loop import (
    ReActLoop,
    ExponentialBackoff,
    ReActResult,
    ReActStep,
)


def dummy_tool(x: int) -> int:
    return x * 2


def failing_tool(x: int) -> int:
    raise RuntimeError("boom")


def test_exponential_backoff_delays():
    backoff = ExponentialBackoff(base_delay=1.0, max_delay=8.0, multiplier=2.0)
    delays = [backoff.get_delay() for _ in range(4)]
    assert delays[0] < 2.0
    assert delays[1] < 4.0
    assert delays[2] < 8.0
    assert delays[3] <= 8.0 + 0.1 * 8.0
    backoff.reset()
    assert backoff.attempt == 0


def test_react_loop_finish_action():
    tools = {"multiply": dummy_tool}
    loop = ReActLoop(tools=tools, max_iterations=5)

    def llm(query: str, steps):
        if not steps:
            return "Thought: multiply by 2\nAction: multiply\nAction Input: {\"x\": 3}"
        return "Thought: done\nAction: finish\nAction Input: {\"answer\": \"6\"}"

    result = loop.run("test", llm)
    assert result.success
    assert result.final_answer == "6"
    assert len(result.steps) == 2


def test_react_loop_unknown_tool():
    tools = {}
    loop = ReActLoop(tools=tools, max_iterations=5)

    def llm(query: str, steps):
        return "Thought: unknown tool\nAction: unknown\nAction Input: {}"

    result = loop.run("test", llm)
    assert not result.success
    assert any("Unknown tool" in (s.observation or "") for s in result.steps)


def test_react_loop_error_handling_and_backoff():
    tools = {"fail": failing_tool}
    loop = ReActLoop(tools=tools, max_iterations=3)

    def llm(query: str, steps):
        return "Thought: fail\nAction: fail\nAction Input: {\"x\": 1}"

    result = loop.run("test", llm)
    assert not result.success
    assert result.iterations == 3
    assert all(s.error == "boom" for s in result.steps if s.error)


def test_react_result_timing_and_iterations():
    steps = [ReActStep(thought="t"), ReActStep(thought="t2")]
    result = ReActResult(steps=steps, final_answer="done", success=True, total_time=0.5, iterations=2)
    assert result.total_time > 0
    assert result.iterations == 2
