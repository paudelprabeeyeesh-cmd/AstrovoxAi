import pytest
import json
from agentic_loop.programmatic_tool_calling import ProgrammaticToolCaller, CodeCall


def dummy_tool(x: int) -> int:
    return x + 1


def test_generate_call_parsing():
    caller = ProgrammaticToolCaller(
        tools={"add": dummy_tool},
        tool_schemas={"add": {"parameters": {"x": "int"}}},
    )

    def llm(prompt, ctx):
        return json.dumps({
            "code": "add(x=1)",
            "tool_name": "add",
            "arguments": {"x": 1},
        })

    call = caller.generate_call("add one", llm)
    assert call.tool_name == "add"
    assert call.arguments == {"x": 1}


def test_execute_call_success():
    caller = ProgrammaticToolCaller(
        tools={"add": dummy_tool},
        tool_schemas={"add": {"parameters": {"x": "int"}}},
    )
    call = CodeCall(code="add(x=5)", tool_name="add", arguments={"x": 5})
    result = caller.execute_call(call)
    assert result == 6


def test_execute_call_invalid_tool():
    caller = ProgrammaticToolCaller(tools={}, tool_schemas={})
    call = CodeCall(code="missing()", tool_name="missing", arguments={})
    with pytest.raises(ValueError):
        caller.execute_call(call)


def test_execute_call_syntax_error():
    caller = ProgrammaticToolCaller(
        tools={"add": dummy_tool},
        tool_schemas={"add": {"parameters": {"x": "int"}}},
    )
    call = CodeCall(code="add(x=(", tool_name="add", arguments={"x": 1})
    with pytest.raises(ValueError):
        caller.execute_call(call)
