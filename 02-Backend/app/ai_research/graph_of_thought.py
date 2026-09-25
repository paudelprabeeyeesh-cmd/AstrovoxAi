"""Graph-of-Thought planning with entity/relationship tracking."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Thought:
    id: str
    content: str
    kind: str = "thought"
    depends_on: list[str] = field(default_factory=list)
    score: float = 0.0


class GraphOfThought:
    def __init__(self) -> None:
        self.thoughts: dict[str, Thought] = {}
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def plan(self, goal: str, constraints: list[str] | None = None) -> list[Thought]:
        self.thoughts = {}
        steps = self._decompose(goal, constraints or [])
        for idx, step in enumerate(steps):
            thought_id = f"step_{idx}"
            depends = [f"step_{idx-1}"] if idx > 0 else []
            self.thoughts[thought_id] = Thought(id=thought_id, content=step, kind="plan", depends_on=depends)
        return list(self.thoughts.values())

    def _decompose(self, goal: str, constraints: list[str]) -> list[str]:
        try:
            client = self._get_client()
            result = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {"role": "system", "content": "Break the goal into a concise numbered plan."},
                    {"role": "user", "content": f"Goal:\n{goal}\n\nConstraints:\n" + "\n".join(constraints)},
                ],
                temperature=0.2,
                max_tokens=512,
            )
            text = result.choices[0].message.content or ""
            return [line.strip("- ") for line in text.splitlines() if line.strip()]
        except Exception as exc:
            logger.error("GoT decomposition failed: %s", exc)
            return [goal]

    def visualize(self) -> dict[str, Any]:
        nodes = [
            {
                "id": thought.id,
                "label": thought.content,
                "kind": thought.kind,
                "score": thought.score,
            }
            for thought in self.thoughts.values()
        ]
        edges = [
            {"from": thought.id, "to": dep}
            for thought in self.thoughts.values()
            for dep in thought.depends_on
            if dep in self.thoughts
        ]
        return {"nodes": nodes, "edges": edges}
