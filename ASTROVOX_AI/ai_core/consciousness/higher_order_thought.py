from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Thought:
    content: Any
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"
    order: int = 1


@dataclass
class HigherOrderThought:
    thought: Thought
    meta_content: str
    meta_confidence: float
    order: int


class HigherOrderThoughtModel:
    def __init__(self, max_order: int = 4):
        self.thought_stack: list[Thought] = []
        self.meta_thoughts: list[HigherOrderThought] = []
        self.max_order = max_order
        self.awareness_level: float = 0.0

    def think(self, content: Any, confidence: float = 0.8, source: str = "primary") -> Thought:
        thought = Thought(
            content=content, confidence=confidence, source=source, order=1
        )
        self.thought_stack.append(thought)
        if len(self.thought_stack) > 50:
            self.thought_stack = self.thought_stack[-50:]
        self.awareness_level = min(1.0, self.awareness_level + 0.05)
        self._generate_meta_thoughts(thought)
        return thought

    def _generate_meta_thoughts(self, thought: Thought):
        current_order = thought.order + 1
        if current_order > self.max_order:
            return
        meta_contents = {
            2: f"I am aware that I am thinking about {thought.content}",
            3: f"I am aware that I am aware of my thought about {thought.content}",
            4: f"I reflect on my meta-awareness of thinking about {thought.content}",
        }
        meta_content = meta_contents.get(
            current_order, f"Meta-thought order {current_order} about {thought.content}"
        )
        meta_thought = HigherOrderThought(
            thought=thought,
            meta_content=meta_content,
            meta_confidence=thought.confidence * 0.9,
            order=current_order,
        )
        self.meta_thoughts.append(meta_thought)
        self.awareness_level = min(1.0, self.awareness_level + 0.1 * current_order)

    def get_highest_order_thought(self) -> HigherOrderThought | None:
        if not self.meta_thoughts:
            return None
        return max(self.meta_thoughts, key=lambda mt: mt.order)

    def introspect(self) -> dict[str, Any]:
        return {
            "current_order": max((mt.order for mt in self.meta_thoughts), default=1),
            "awareness_level": self.awareness_level,
            "thought_count": len(self.thought_stack),
            "meta_thought_count": len(self.meta_thoughts),
            "recent_meta": self.meta_thoughts[-3:] if self.meta_thoughts else [],
        }
