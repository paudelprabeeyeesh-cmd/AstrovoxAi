from typing import Any, Callable, Optional


class SandboxExecutor:
    def execute(self, code: str, inputs: Optional[dict] = None) -> Any:
        if inputs is None:
            inputs = {}
        allowed_names = {"__builtins__": {}}
        allowed_names.update(inputs)
        local_vars = {}
        try:
            exec(code, allowed_names, local_vars)
        except Exception as _e:  # noqa: BLE001
            return {"error": str(_e)}
        result = local_vars.get("result")
        if result is None and "print" not in code:
            return local_vars
        return result

    def execute_with_trace(self, code: str, inputs: Optional[dict] = None) -> dict:
        if inputs is None:
            inputs = {}
        trace = {"code": code, "inputs": inputs}
        try:
            result = self.execute(code, inputs)
            trace["result"] = result
            trace["error"] = None
        except Exception as _e:  # noqa: BLE001
            trace["result"] = None
            trace["error"] = str(_e)
        return trace


class PAL:
    def __init__(self, generate_code_fn: Callable[[str], str], executor: Optional[SandboxExecutor] = None):
        self.generate_code_fn = generate_code_fn
        self.executor = executor or SandboxExecutor()

    def generate_code(self, prompt: str) -> str:
        return self.generate_code_fn(prompt)

    def execute(self, code: str, inputs: Optional[dict] = None) -> Any:
        return self.executor.execute(code, inputs)

    def run(self, prompt: str, inputs: Optional[dict] = None) -> dict:
        code = self.generate_code(prompt)
        result = self.execute(code, inputs)
        return {"code": code, "result": result}

    def score_execution(self, prompt: str, expected: Any, inputs: Optional[dict] = None) -> float:
        out = self.run(prompt, inputs)
        result = out.get("result")
        if result is None:
            return 0.0
        if isinstance(result, (int, float)) and isinstance(expected, (int, float)):
            return float(1.0 / (1.0 + abs(float(result) - float(expected))))
        return 1.0 if str(result) == str(expected) else 0.0
