"""Predictive Text Completion - Completes text across all interfaces."""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class CompletionSuggestion:
    suggestion_id: str
    text: str
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)
    interface: str = "universal"
    timestamp: float = field(default_factory=time.time)


class PredictiveTextCompletion:
    """Predicts and completes text across all interfaces."""

    def __init__(self):
        self._suggestions: Dict[str, List[CompletionSuggestion]] = defaultdict(list)
        self._completion_history: List[Dict[str, Any]] = []
        self._context_window: Dict[str, List[str]] = defaultdict(list)

    def get_suggestions(self, prefix: str, context: List[str] = None, interface: str = "universal", limit: int = 10) -> List[CompletionSuggestion]:
        key = f"{interface}:{prefix.lower()}"
        suggestions = self._suggestions.get(key, [])
        if context:
            context_key = " ".join(context).lower()
            ctx_suggestions = self._suggestions.get(f"ctx:{context_key}", [])
            suggestions = suggestions + ctx_suggestions
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return suggestions[:limit]

    def add_suggestion(self, prefix: str, text: str, confidence: float, interface: str = "universal") -> str:
        suggestion_id = str(uuid.uuid4())
        suggestion = CompletionSuggestion(
            suggestion_id=suggestion_id,
            text=text,
            confidence=confidence,
            interface=interface,
        )
        key = f"{interface}:{prefix.lower()}"
        self._suggestions[key].append(suggestion)
        self._completion_history.append({
            "prefix": prefix,
            "text": text,
            "confidence": confidence,
            "interface": interface,
            "timestamp": time.time(),
        })
        return suggestion_id

    def record_completion(self, prefix: str, selected: str, interface: str = "universal") -> None:
        self.add_suggestion(prefix, selected, 1.0, interface)
        ctx_key = f"ctx:{prefix.lower()}"
        self._context_window[ctx_key].append(selected)
        if len(self._context_window[ctx_key]) > 50:
            self._context_window[ctx_key] = self._context_window[ctx_key][-50:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "suggestions": sum(len(v) for v in self._suggestions.values()),
            "completion_history": len(self._completion_history),
            "context_windows": len(self._context_window),
        }
