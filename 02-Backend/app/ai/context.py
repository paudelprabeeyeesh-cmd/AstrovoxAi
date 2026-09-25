"""Context builder for LLM requests."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Build LLM context from system prompt, history, and retrieved documents."""

    def __init__(self, max_context_tokens: int = 8000) -> None:
        self.max_context_tokens = max_context_tokens

    def build(
        self,
        system_prompt: str,
        history: List[Dict[str, str]],
        documents: Optional[List[Dict[str, str]]] = None,
        user_message: str = "",
    ) -> str:
        context_parts = [f"System: {system_prompt}"]
        if documents:
            context_parts.append("Context:")
            for i, doc in enumerate(documents[:3], 1):
                context_parts.append(f"[{i}] {doc.get('content', '')[:500]}")
        for msg in history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            context_parts.append(f"{role.capitalize()}: {content[:500]}")
        if user_message:
            context_parts.append(f"User: {user_message}")
        return "\n\n".join(context_parts)

    def estimate_tokens(self, context: str) -> int:
        return len(context.split()) * 1.3


_context_builder = ContextBuilder()


def get_context_builder() -> ContextBuilder:
    return _context_builder
