from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import torch
import torch.nn as nn

# ---------------------------------------------------------------------------
# 1. Tool Registry
# ---------------------------------------------------------------------------


class Tool:
    """Registered tool with name, description, and callable implementation."""

    def __init__(self, name: str, description: str, func: Callable, parameters: dict | None = None):
        self.name = name
        self.description = description
        self.func = func
        self.parameters = parameters or {}

    def __call__(self, **kwargs: Any) -> Any:
        return self.func(**kwargs)

    def to_schema(self) -> dict:
        return {"name": self.name, "description": self.description, "parameters": self.parameters}


class ToolRegistry:
    """Registry of available tools for agent use."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def to_schema(self) -> list[dict]:
        return [tool.to_schema() for tool in self._tools.values()]


# ---------------------------------------------------------------------------
# 2. ReAct Agent Loop
# ---------------------------------------------------------------------------


@dataclass
class AgentStep:
    thought: str
    action: str | None
    action_input: str | None
    observation: str | None


class ReActAgent:
    """ReAct-style reasoning and acting agent."""

    def __init__(
        self,
        model: nn.Module,
        tokenizer: object,
        tool_registry: ToolRegistry,
        max_steps: int = 16,
        device: torch.device | None = None,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.device = device or next(model.parameters()).device

    def _parse_action(self, text: str) -> tuple[str, str] | None:
        if "Action:" in text and "Action Input:" in text:
            action = text.split("Action:")[1].split("Action Input:")[0].strip()
            action_input = text.split("Action Input:")[1].split("Observation:")[0].strip()
            return action, action_input
        return None

    def run(self, prompt: str) -> str:
        context = prompt
        for _ in range(self.max_steps):
            inputs = self._encode(context)
            with torch.no_grad():
                outputs = self.model.generate(**inputs, max_new_tokens=512, temperature=0.1)
            text = self._decode(outputs)
            new_part = text[len(context):]
            context = text
            action_data = self._parse_action(new_part)
            if action_data is None:
                return text
            action_name, action_input = action_data
            tool = self.tool_registry.get(action_name)
            if tool is None:
                observation = f"Error: tool {action_name} not found"
            else:
                try:
                    kwargs = json.loads(action_input) if action_input.startswith("{") else {"query": action_input}
                    result = tool(**kwargs)
                    observation = str(result)
                except Exception as e:
                    observation = f"Error: {e}"
            context += f"\nObservation: {observation}\nThought:"
        return context

    def _encode(self, text: str) -> dict:
        if hasattr(self.tokenizer, "apply_chat_template"):
            messages = [{"role": "user", "content": text}]
            input_ids = self.tokenizer.apply_chat_template(messages, return_tensors="pt").to(self.device)
            return {"input_ids": input_ids}
        if hasattr(self.tokenizer, "encode"):
            ids = self.tokenizer.encode(text)
            return {"input_ids": torch.tensor([ids], device=self.device, dtype=torch.long)}
        return {"input_ids": torch.zeros(1, 1, device=self.device, dtype=torch.long)}

    def _decode(self, outputs: torch.Tensor) -> str:
        if hasattr(self.tokenizer, "decode"):
            return self.tokenizer.decode(outputs[0].tolist())
        return " ".join(str(tok) for tok in outputs[0].tolist())


# ---------------------------------------------------------------------------
# 3. Function Calling Agent
# ---------------------------------------------------------------------------


class FunctionCallingAgent:
    """Structured function-calling agent."""

    def __init__(
        self,
        model: nn.Module,
        tokenizer: object,
        tool_registry: ToolRegistry,
        max_iterations: int = 8,
        device: torch.device | None = None,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations
        self.device = device or next(model.parameters()).device

    def _call_tool(self, tool_name: str, arguments: dict) -> str:
        tool = self.tool_registry.get(tool_name)
        if tool is None:
            return f"Error: tool {tool_name} not found"
        try:
            result = tool(**arguments)
            return str(result)
        except Exception as e:
            return f"Error executing {tool_name}: {e}"

    def run(self, prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        for _ in range(self.max_iterations):
            inputs = self._encode(messages)
            with torch.no_grad():
                outputs = self.model.generate(**inputs, max_new_tokens=512, temperature=0.1)
            response_text = self._decode(outputs)
            messages.append({"role": "assistant", "content": response_text})
            try:
                tool_call = json.loads(response_text)
                if "tool" in tool_call and "arguments" in tool_call:
                    observation = self._call_tool(tool_call["tool"], tool_call["arguments"])
                    messages.append({"role": "tool", "content": observation})
                    continue
            except (json.JSONDecodeError, KeyError):
                pass
            return response_text
        return messages[-1].get("content", "")

    def _encode(self, messages: list[dict]) -> dict:
        if hasattr(self.tokenizer, "apply_chat_template"):
            input_ids = self.tokenizer.apply_chat_template(messages, return_tensors="pt").to(self.device)
            return {"input_ids": input_ids}
        return {"input_ids": torch.zeros(1, 1, device=self.device, dtype=torch.long)}

    def _decode(self, outputs: torch.Tensor) -> str:
        if hasattr(self.tokenizer, "decode"):
            return self.tokenizer.decode(outputs[0].tolist())
        return " ".join(str(tok) for tok in outputs[0].tolist())


# ---------------------------------------------------------------------------
# 4. Agent State
# ---------------------------------------------------------------------------


@dataclass
class AgentState:
    prompt: str
    history: list[dict]
    done: bool = False
    metadata: dict | None = None
