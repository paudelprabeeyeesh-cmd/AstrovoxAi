"""Astravox AI orchestrator for prompt composition and streaming."""
from typing import Any, Dict, Iterable, List, Optional

from .context_manager import extract_recent_turns
from .response_handler import assemble_prompt, format_response
from .gemini import get_ai_response as gemini_get_ai_response, get_ai_stream as gemini_get_ai_stream


class AIOrchestrator:
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name

    def _build_prompt(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        memory_history: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        conversation_history = conversation_history or []
        memory_history = memory_history or []
        recent_history = extract_recent_turns(conversation_history, max_turns=12)
        prompt = assemble_prompt(user_message, recent_history)

        if memory_history:
            memory_lines = [
                f"- {entry.get('message', '').strip()}"
                for entry in memory_history[-8:]
                if entry.get('message')
            ]
            if memory_lines:
                prompt += "\n\nShort-term memory:\n" + "\n".join(memory_lines)

        return prompt

    def stream(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        memory_history: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Iterable[str]:
        prompt = self._build_prompt(user_message, conversation_history, memory_history)
        for chunk in gemini_get_ai_stream(prompt, **kwargs):
            yield format_response(chunk)

    def generate(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        memory_history: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> str:
        prompt = self._build_prompt(user_message, conversation_history, memory_history)
        return format_response(gemini_get_ai_response(prompt, **kwargs))


def get_ai_stream(
    user_message: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    memory_history: Optional[List[Dict[str, Any]]] = None,
    **kwargs,
) -> Iterable[str]:
    return AIOrchestrator().stream(user_message, conversation_history, memory_history, **kwargs)


def get_ai_response(
    user_message: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    memory_history: Optional[List[Dict[str, Any]]] = None,
    **kwargs,
) -> str:
    return AIOrchestrator().generate(user_message, conversation_history, memory_history, **kwargs)


def build_prompt(
    user_message: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    memory_history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return AIOrchestrator()._build_prompt(user_message, conversation_history, memory_history)
