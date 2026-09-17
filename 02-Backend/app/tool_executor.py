import logging
from typing import Any

from .tools import get_builtin_tools

logger = logging.getLogger(__name__)


class ToolExecutor:
    def __init__(self):
        self._tools = {t.name: t.function for t in get_builtin_tools()}

    def execute_tool(self, tool_name: str, arguments: dict[str, Any], user_id: str) -> str:
        func = self._tools.get(tool_name)
        if not func:
            return f"Error: tool '{tool_name}' not found"
        try:
            if tool_name in ("search_documents", "create_memory"):
                return func(user_id=user_id, **arguments)
            return func(**arguments)
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return f"Error executing {tool_name}: {e}"

    def validate_arguments(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        func = self._tools.get(tool_name)
        if not func:
            return False
        import inspect
        sig = inspect.signature(func)
        required = [
            p.name for p in sig.parameters.values()
            if p.default == inspect.Parameter.empty
        ]
        return all(k in arguments for k in required)

    def get_available_tools(self, user_id: str) -> list[dict[str, Any]]:
        from .tools import get_builtin_tools
        tools = []
        for t in get_builtin_tools():
            schema = t.to_openai_schema()
            if t.name in ("search_documents", "create_memory"):
                schema["function"]["parameters"]["properties"]["user_id"] = {
                    "type": "string",
                    "description": f"User ID ({user_id})",
                }
            tools.append(schema)
        return tools
