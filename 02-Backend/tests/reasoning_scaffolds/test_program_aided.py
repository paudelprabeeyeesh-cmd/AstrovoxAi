from __future__ import annotations

from typing import Optional

import pytest

from reasoning_scaffolds.program_aided import CodeProgram, program_aided


def test_syntax_valid():
    p = CodeProgram("x = 1")
    assert p.is_syntax_valid() is True


def test_syntax_invalid():
    p = CodeProgram("x = = 1")
    assert p.is_syntax_valid() is False


def test_execute_sets_output():
    p = CodeProgram("result = 40 + 2")
    p.execute()
    assert p.error is None
    assert p.output == 42


def test_execute_captures_error():
    p = CodeProgram("raise ValueError('bad')")
    p.execute()
    assert p.error is not None


def test_program_aided_success():
    def gen(problem: str) -> str:
        return "result = 10 * 10"

    def execute(code: str) -> Optional[str]:
        p = CodeProgram(code)
        p.execute()
        return str(p.output)

    def extract(output: Optional[str]) -> Optional[str]:
        return output

    answer, program = program_aided("10*10", gen, execute, extract, max_attempts=2)
    assert answer == "100"
    assert program is not None
