"""Context engine: builds the model input for every request.

The engine unifies memory, retrieval, history, and tool outputs into a
single, token-budgeted context block consumed by the model router.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from .artifacts import Artifact, ArtifactType
from .bus import get_event_bus


class ContextSection(str, Enum):
    SYSTEM = "system"
    HISTORY = "history"
    MEMORY = "memory"
    RETRIEVAL = "retrieval"
    TOOL_OUTPUTS = "tool_outputs"
    USER_PREFERENCES = "user_preferences"
    INSTRUCTIONS = "instructions"


@dataclass
class ContextBlock:
    section: ContextSection
    content: str
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    tokens: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section": self.section.value,
            "content": self.content,
            "weight": self.weight,
            "metadata": self.metadata,
            "tokens": self.tokens,
        }


@dataclass
class ContextBudget:
    max_tokens: int = 8000
    reserve_for_response: int = 1024
    section_limits: Dict[ContextSection, int] = field(default_factory=dict)

    def available(self) -> int:
        return max(self.max_tokens - self.reserve_for_response, 0)


class TokenEstimator:
    """Cheap word-based token estimator (real deployments can swap in tiktoken)."""

    def estimate(self, text: str) -> int:
        if not text:
            return 0
        return max(1, int(len(text.split()) * 1.3))


@dataclass
class ContextItem:
    """Lightweight reference used by the engine to dedupe + rank."""

    key: str
    content: str
    section: ContextSection
    weight: float = 1.0
    tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextEngine:
    """Builds a single context payload for the model router."""

    def __init__(self, estimator: Optional[TokenEstimator] = None) -> None:
        self.estimator = estimator or TokenEstimator()
        self._sources: List[Callable[[Dict[str, Any]], List[ContextItem]]] = []
        self._seen: "OrderedDict[str, None]" = OrderedDict()

    def register_source(
        self, source: Callable[[Dict[str, Any]], List[ContextItem]]
    ) -> None:
        self._sources.append(source)

    def build(
        self,
        request: Dict[str, Any],
        budget: Optional[ContextBudget] = None,
    ) -> List[ContextBlock]:
        budget = budget or ContextBudget()
        items: List[ContextItem] = []
        for source in self._sources:
            try:
                items.extend(source(request))
            except Exception:
                continue

        # Deduplicate by content hash, then rank by weight.
        deduped: List[ContextItem] = []
        for item in items:
            fingerprint = f"{item.section.value}:{hash(item.content)}"
            if fingerprint in self._seen:
                continue
            self._seen[fingerprint] = None
            deduped.append(item)
        deduped.sort(key=lambda it: it.weight, reverse=True)

        available = budget.available()
        per_section: Dict[ContextSection, int] = dict(budget.section_limits or {})
        used: Dict[ContextSection, int] = {s: 0 for s in ContextSection}
        blocks: List[ContextBlock] = []
        consumed = 0

        for item in deduped:
            tokens = self.estimator.estimate(item.content)
            item.tokens = tokens
            cap = per_section.get(item.section, available)
            if used[item.section] + tokens > cap:
                continue
            if consumed + tokens > available:
                continue
            blocks.append(
                ContextBlock(
                    section=item.section,
                    content=item.content,
                    weight=item.weight,
                    metadata=item.metadata,
                    tokens=tokens,
                )
            )
            used[item.section] += tokens
            consumed += tokens

        # System + history always at the top; rest appended in order found.
        blocks.sort(
            key=lambda b: [
                ContextSection.SYSTEM,
                ContextSection.INSTRUCTIONS,
                ContextSection.USER_PREFERENCES,
                ContextSection.MEMORY,
                ContextSection.RETRIEVAL,
                ContextSection.TOOL_OUTPUTS,
                ContextSection.HISTORY,
            ].index(b.section)
        )
        get_event_bus().publish(
            "context.built",
            {
                "request_id": request.get("request_id"),
                "blocks": len(blocks),
                "tokens": consumed,
            },
            source="kernel.context",
        )
        return blocks

    def render(self, blocks: Sequence[ContextBlock]) -> str:
        parts: List[str] = []
        for block in blocks:
            parts.append(f"[{block.section.value}]\n{block.content}")
        return "\n\n".join(parts)


# ---- default source factories ----------------------------------------------


def history_source(messages: List[Dict[str, Any]]) -> Callable[[Dict[str, Any]], List[ContextItem]]:
    def _source(_request: Dict[str, Any]) -> List[ContextItem]:
        return [
            ContextItem(
                key=f"history:{i}",
                content=f"{m.get('role', 'user')}: {m.get('content', '')}",
                section=ContextSection.HISTORY,
                weight=1.0 + i * 0.1,
                metadata={"index": i},
            )
            for i, m in enumerate(messages)
        ]

    return _source


def memory_source(memories: List[Dict[str, Any]]) -> Callable[[Dict[str, Any]], List[ContextItem]]:
    def _source(_request: Dict[str, Any]) -> List[ContextItem]:
        return [
            ContextItem(
                key=f"memory:{m.get('id', i)}",
                content=str(m.get("content", "")),
                section=ContextSection.MEMORY,
                weight=float(m.get("importance", 1.0)),
                metadata=m,
            )
            for i, m in enumerate(memories)
        ]

    return _source


def retrieval_source(docs: List[Dict[str, Any]]) -> Callable[[Dict[str, Any]], List[ContextItem]]:
    def _source(_request: Dict[str, Any]) -> List[ContextItem]:
        return [
            ContextItem(
                key=f"doc:{d.get('id', i)}",
                content=str(d.get("content", "")),
                section=ContextSection.RETRIEVAL,
                weight=float(d.get("score", 1.0)),
                metadata=d,
            )
            for i, d in enumerate(docs)
        ]

    return _source


def tool_source(tool_outputs: List[Dict[str, Any]]) -> Callable[[Dict[str, Any]], List[ContextItem]]:
    def _source(_request: Dict[str, Any]) -> List[ContextItem]:
        return [
            ContextItem(
                key=f"tool:{t.get('id', i)}",
                content=f"Tool {t.get('name', '')}: {t.get('output', '')}",
                section=ContextSection.TOOL_OUTPUTS,
                weight=1.5,
                metadata=t,
            )
            for i, t in enumerate(tool_outputs)
        ]

    return _source


def instruction_source(instruction: str) -> Callable[[Dict[str, Any]], List[ContextItem]]:
    def _source(_request: Dict[str, Any]) -> List[ContextItem]:
        return [
            ContextItem(
                key="instruction",
                content=instruction,
                section=ContextSection.INSTRUCTIONS,
                weight=10.0,
            )
        ]

    return _source


def system_source(system: str) -> Callable[[Dict[str, Any]], List[ContextItem]]:
    def _source(_request: Dict[str, Any]) -> List[ContextItem]:
        return [
            ContextItem(
                key="system",
                content=system,
                section=ContextSection.SYSTEM,
                weight=100.0,
            )
        ]

    return _source


def preferences_source(prefs: Dict[str, Any]) -> Callable[[Dict[str, Any]], List[ContextItem]]:
    def _source(_request: Dict[str, Any]) -> List[ContextItem]:
        if not prefs:
            return []
        return [
            ContextItem(
                key="preferences",
                content="; ".join(f"{k}={v}" for k, v in prefs.items()),
                section=ContextSection.USER_PREFERENCES,
                weight=2.0,
            )
        ]

    return _source