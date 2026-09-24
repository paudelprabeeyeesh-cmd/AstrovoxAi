import pytest
from sandboxing.code_executor import CodeExecutor, ExecutionResult


def test_run_simple_expression():
    executor = CodeExecutor()
    result = executor.run("1 + 1")
    assert result.success is True
    assert result.error == ""


def test_run_print_captures_output():
    executor = CodeExecutor()
    result = executor.run("print('hello')")
    assert result.success is True
    assert "hello" in result.output


def test_run_multiple_prints():
    executor = CodeExecutor()
    result = executor.run("print('a'); print('b')")
    assert result.success is True
    assert "a" in result.output
    assert "b" in result.output


def test_run_syntax_error():
    executor = CodeExecutor()
    result = executor.run("1 +")
    assert result.success is False
    assert "SyntaxError" in result.error


def test_run_runtime_error():
    executor = CodeExecutor()
    result = executor.run("1 / 0")
    assert result.success is False
    assert "ZeroDivisionError" in result.error


def test_run_with_custom_globals():
    executor = CodeExecutor()
    globs = {"__name__": "__main__", "x": 10}
    result = executor.run("y = x + 5", globals_=globs)
    assert result.success is True
    assert globs["y"] == 15


def test_run_assignment():
    executor = CodeExecutor()
    result = executor.run("x = 42")
    assert result.success is True


def test_run_no_output():
    executor = CodeExecutor()
    result = executor.run("x = 1")
    assert result.success is True
    assert result.output == ""


def test_run_empty_code():
    executor = CodeExecutor()
    result = executor.run("")
    assert result.success is True


def test_run_multiline_code():
    executor = CodeExecutor()
    result = executor.run("x = 1\ny = 2\nprint(x + y)")
    assert result.success is True
    assert "3" in result.output


def test_execution_result_fields():
    result = ExecutionResult(success=True, output="hi", error="")
    assert result.success is True
    assert result.output == "hi"
    assert result.error == ""


def test_run_with_none_globals():
    executor = CodeExecutor()
    result = executor.run("1 + 1", globals_=None)
    assert result.success is True
