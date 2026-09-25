import json
import logging
from typing import Any

from .tool_executor import ToolExecutor

logger = logging.getLogger(__name__)


class FunctionCallingHandler:
    def __init__(self):
        self.executor = ToolExecutor()

    def detect_function_call(self, response: dict) -> dict | None:
        if response.get("choices"):
            message = response["choices"][0]["message"]
            if message.get("tool_calls"):
                return message
        return None

    def parse_tool_calls(self, response: dict) -> list[dict[str, Any]]:
        tool_calls = []
        if response.get("choices"):
            message = response["choices"][0]["message"]
            raw_calls = message.get("tool_calls", [])
            for call in raw_calls:
                func = call.get("function", {})
                arguments = func.get("arguments", "{}")
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = {}
                tool_calls.append({
                    "id": call.get("id"),
                    "name": func.get("name"),
                    "arguments": arguments,
                })
        return tool_calls

    def execute_tools(self, tool_calls: list[dict[str, Any]], user_id: str) -> list[dict[str, Any]]:
        results = []
        for call in tool_calls:
            name = call["name"]
            args = call.get("arguments", {})
            result = self.executor.execute_tool(name, args, user_id)
            results.append({
                "tool_call_id": call.get("id"),
                "role": "tool",
                "name": name,
                "content": result,
            })
        return results

    def format_tool_results(self, tool_results: list[dict[str, Any]]) -> str:
        parts = []
        for r in tool_results:
            parts.append(f"[{r['name']} result: {r['content']}]")
        return "\n".join(parts)

    def handle_function_calling_loop(self, prompt: str, user_id: str, max_iterations: int = 5) -> tuple[str, str, str]:
        from app.core.router import call_llm

        tools = self.executor.get_available_tools(user_id)
        messages = [{"role": "user", "content": prompt}]
        model = "auto"
        provider = "function-calling"

        for _ in range(max_iterations):
            try:
                response = call_llm(
                    messages=messages,
                    tools=tools,
                    timeout=30,
                )
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                return f"Error: {e}", model, provider

            text = response.get("text", "")
            tool_calls = response.get("tool_calls", [])
            model = response.get("model", model)
            provider = response.get("provider", provider)

            if not tool_calls:
                return text, model, provider

            if response.get("choices"):
                msg = response["choices"][0]["message"]
                messages.append({
                    "role": msg.get("role", "assistant"),
                    "content": msg.get("content"),
                    "tool_calls": msg.get("tool_calls"),
                })

            tool_results = self.execute_tools(tool_calls, user_id)
            for r in tool_results:
                messages.append({
                    "role": r["role"],
                    "content": r["content"],
                    "name": r["name"],
                })

        try:
            final = call_llm(
                messages=messages,
                timeout=30,
            )
            return final.get("text", ""), final.get("model", model), final.get("provider", provider)
        except Exception as e:
            logger.error(f"Final LLM call failed: {e}")
            return self.format_tool_results(tool_results), model, provider
