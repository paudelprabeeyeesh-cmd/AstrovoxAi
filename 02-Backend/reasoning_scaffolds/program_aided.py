from __future__ import annotations

import ast
import traceback
from typing import Callable, List, Optional, Tuple


class CodeProgram:
    def __init__(self, code: str = "") -> None:
        self.code = code
        self.output: Optional[str] = None
        self.error: Optional[str] = None

    def execute(self, globals_dict: Optional[dict] = None, locals_dict: Optional[dict] = None) -> None:
        globals_dict = globals_dict or {}
        locals_dict = locals_dict or {}
        try:
            compiled = compile(self.code, "<string>", "exec")
            exec(compiled, globals_dict, locals_dict)  # noqa: S102
            self.output = locals_dict.get("result", None)
        except Exception:
            self.error = traceback.format_exc()

    def is_syntax_valid(self) -> bool:
        try:
            ast.parse(self.code)
            return True
        except SyntaxError:
            return False


def program_aided(
    problem: str,
    generate_code_fn: Callable[[str], str],
    execute_fn: Callable[[str], Optional[str]],
    extract_answer_fn: Callable[[Optional[str]], Optional[str]],
    max_attempts: int = 3,
) -> Tuple[Optional[str], Optional[CodeProgram]]:
    for _ in range(max_attempts):
        code = generate_code_fn(problem)
        program = CodeProgram(code)
        if not program.is_syntax_valid():
            program.error = "SyntaxError"
            continue
        raw_output = execute_fn(code)
        program.output = raw_output
        answer = extract_answer_fn(raw_output)
        if answer is not None:
            return answer, program
    return None, None
