"""
Retrieval-augmented agents with dynamic tool use and multi-step reasoning.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class RetrievalAugmentedAgent:
    def __init__(self, model: nn.Module, retriever: Any, tool_registry: Optional[Dict[str, Any]] = None):
        self.model = model
        self.retriever = retriever
        self.tool_registry = tool_registry or {}
        self.reasoning_steps: List[Dict[str, Any]] = []

    def run(self, query: str, max_steps: int = 5, top_k: int = 5) -> Tuple[str, List[Dict[str, Any]]]:
        context = self.retriever.retrieve(query, top_k=top_k)
        response = self._generate_with_context(query, context)
        step = {'step': 0, 'query': query, 'context': context, 'response': response, 'tool_used': None}
        self.reasoning_steps.append(step)
        for i in range(1, max_steps):
            if self._needs_tool(response):
                tool_name = self._select_tool(response)
                tool_output = self._execute_tool(tool_name, response)
                response = self._generate_with_context(query, context + [tool_output])
                step = {'step': i, 'query': query, 'context': context + [tool_output], 'response': response, 'tool_used': tool_name}
            else:
                break
            self.reasoning_steps.append(step)
        return response, self.reasoning_steps

    def _generate_with_context(self, query: str, context: List[Any]) -> str:
        context_text = "\n".join([str(c) for c in context])
        prompt = f"Context:\n{context_text}\n\nQuery: {query}\n\nResponse:"
        inputs = self._tokenize(prompt)
        with torch.no_grad():
            outputs = self.model(inputs)
        return self._decode(outputs)

    def _needs_tool(self, response: str) -> bool:
        tool_keywords = ['search', 'calculate', 'lookup', 'fetch', 'query']
        return any(kw in response.lower() for kw in tool_keywords)

    def _select_tool(self, response: str) -> str:
        available = list(self.tool_registry.keys())
        if not available:
            return ""
        for tool in available:
            if tool in response.lower():
                return tool
        return available[0]

    def _execute_tool(self, tool_name: str, input_text: str) -> str:
        tool = self.tool_registry.get(tool_name)
        if tool is None:
            return f"Tool {tool_name} not found."
        return str(tool(input_text))

    def _tokenize(self, text: str) -> torch.Tensor:
        return torch.tensor([[ord(c) for c in text[:1024]]], dtype=torch.long)

    def _decode(self, tokens: torch.Tensor) -> str:
        return ''.join([chr(t) for t in tokens[0].tolist() if 0 < t < 256])
