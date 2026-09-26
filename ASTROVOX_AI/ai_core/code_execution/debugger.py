from typing import Optional, Dict, Any, List
import ast
import sys
import traceback
import time
import io
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass, field


@dataclass
class DebugStep:
    line_no: int
    event: str
    locals: Dict[str, Any] = field(default_factory=dict)
    globals: Dict[str, Any] = field(default_factory=dict)
    output: str = ""


@dataclass
class DebugResult:
    success: bool
    output: str
    error: Optional[str]
    steps: List[DebugStep] = field(default_factory=list)
    execution_time_ms: float = 0.0


class CodeDebugger:
    def __init__(self, max_steps: int = 1000, max_output_chars: int = 10000):
        self.max_steps = max_steps
        self.max_output_chars = max_output_chars

    def debug(self, code: str, input_data: Optional[str] = None) -> DebugResult:
        steps: List[DebugStep] = []
        start = time.perf_counter()
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            elapsed = (time.perf_counter() - start) * 1000
            return DebugResult(success=False, output="", error=f"SyntaxError: {e}", steps=[], execution_time_ms=elapsed)
        tracer = _Tracer(steps, self.max_steps)
        try:
            compiled = compile(tree, '<debug>', 'exec')
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                exec(compiled, {'__name__': '__main__', '__debugger__': tracer, 'input': input_data or ''})
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000
            tb = traceback.format_exc()
            return DebugResult(
                success=False,
                output=stdout_buf.getvalue()[-self.max_output_chars:],
                error=tb[-self.max_output_chars:],
                steps=steps,
                execution_time_ms=elapsed,
            )
        elapsed = (time.perf_counter() - start) * 1000
        return DebugResult(
            success=True,
            output=stdout_buf.getvalue()[-self.max_output_chars:],
            error=None,
            steps=steps,
            execution_time_ms=elapsed,
        )

    def get_trace(self, code: str) -> List[DebugStep]:
        result = self.debug(code)
        return result.steps

    def find_first_error_line(self, code: str) -> Optional[int]:
        result = self.debug(code)
        if not result.success and result.error:
            for line in result.error.splitlines():
                if 'line ' in line:
                    try:
                        line_no = int(line.split('line ')[-1].split(',')[0].strip(')'))
                        return line_no
                    except (ValueError, IndexError):
                        continue
        return None


class _Tracer:
    def __init__(self, steps: List[DebugStep], max_steps: int):
        self.steps = steps
        self.max_steps = max_steps

    def trace_calls(self, frame, event, arg):
        if len(self.steps) >= self.max_steps:
            return None
        filename = frame.f_code.co_filename
        if filename in ('<string>', '<debug>'):
            return self.trace_lines
        return None

    def trace_lines(self, frame, event, arg):
        if len(self.steps) >= self.max_steps:
            return None
        if event == 'line':
            local_vars = {k: repr(v) for k, v in frame.f_locals.items()}
            global_vars = {k: repr(v) for k, v in frame.f_globals.items() if not k.startswith('__')}
            step = DebugStep(
                line_no=frame.f_lineno,
                event='line',
                locals=local_vars,
                globals=global_vars,
            )
            self.steps.append(step)
        return self.trace_lines


def profile_code(code: str) -> Dict[str, Any]:
    import cProfile
    import pstats
    import io as _io
    pr = cProfile.Profile()
    pr.enable()
    try:
        exec(compile(ast.parse(code), '<profile>', 'exec'), {'__name__': '__main__'})
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000
        tb = traceback.format_exc()
        logger.warning("profiling failed: %s", tb)
    pr.disable()
    buf = _io.StringIO()
    ps = pstats.Stats(pr, stream=buf).sort_stats('cumulative')
    ps.print_stats(20)
    return {
        'profile': buf.getvalue(),
        'total_calls': ps.total_calls,
    }
