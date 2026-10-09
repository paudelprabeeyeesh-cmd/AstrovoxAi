import ast
import json
from typing import Any, Callable, Dict
from dataclasses import dataclass


@dataclass
class CodeCall:
    code: str
    tool_name: str
    arguments: Dict[str, Any]


class ProgrammaticToolCaller:
    def __init__(self, tools: Dict[str, Callable], tool_schemas: Dict[str, Dict[str, Any]]):
        self.tools = tools
        self.tool_schemas = tool_schemas

    def generate_call(self, query: str, llm_generator: Callable[[str, Dict[str, Any]], str]) -> CodeCall:
        schema_context = json.dumps(self.tool_schemas, indent=2)
        prompt = f"Generate Python code to call the appropriate tool for: {query}\n\nAvailable tools:\n{schema_context}\n\nReturn JSON with code, tool_name, and arguments."
        response = llm_generator(prompt, {})
        try:
            data = json.loads(response)
            return CodeCall(code=data.get("code", ""), tool_name=data.get("tool_name", ""), arguments=data.get("arguments", {}))
        except Exception as _e:  # noqa: BLE001
            return CodeCall(code="", tool_name="", arguments={})

    def execute_call(self, call: CodeCall) -> Any:
        if not call.code or call.tool_name not in self.tools:
            raise ValueError(f"Invalid call: tool={call.tool_name}")
        try:
            ast.parse(call.code)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in generated code: {e}") from None
        return self.tools[call.tool_name](**call.arguments)
