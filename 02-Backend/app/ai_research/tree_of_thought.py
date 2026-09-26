"""Tree-of-Thought reasoning orchestrator."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ThoughtNode:
    thought: str
    score: float = 0.0
    children: list[ThoughtNode] = field(default_factory=list)
    is_terminal: bool = False
    result: str | None = None


class TreeOfThought:
    def __init__(self, max_depth: int = 3, branching_factor: int = 3) -> None:
        self.max_depth = max_depth
        self.branching_factor = branching_factor
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def reason(self, problem: str, context: str | None = None) -> str:
        root = ThoughtNode(thought=problem)
        self._expand(root, context, depth=0)
        best = self._select_best(root)
        return best.result or best.thought

    def _expand(self, node: ThoughtNode, context: str | None, depth: int) -> None:
        if depth >= self.max_depth:
            node.is_terminal = True
            node.result = self._synthesize(node.thought, context)
            node.score = self._score(node.thought, node.result)
            return
        thoughts = self._generate_thoughts(node.thought, context, self.branching_factor)
        for thought in thoughts:
            child = ThoughtNode(thought=thought)
            node.children.append(child)
            self._expand(child, context, depth + 1)

    def _generate_thoughts(self, parent_thought: str, context: str | None, n: int) -> list[str]:
        try:
            client = self._get_client()
            result = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {"role": "system", "content": f"Generate {n} concise next-step thoughts for this reasoning chain."},
                    {"role": "user", "content": f"Current thought:\n{parent_thought}\n\nContext:\n{context or 'None'}"},
                ],
                temperature=0.7,
                max_tokens=256,
            )
            text = result.choices[0].message.content or ""
            return [line.strip("- ") for line in text.splitlines() if line.strip()][:n]
        except Exception as exc:
            logger.error("ToT thought generation failed: %s", exc)
            return [f"Consider alternative approach {i+1}" for i in range(n)]

    def _synthesize(self, thought: str, context: str | None) -> str:
        try:
            client = self._get_client()
            result = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {"role": "system", "content": "Synthesize the reasoning into a final concise answer."},
                    {"role": "user", "content": f"Thought:\n{thought}\n\nContext:\n{context or 'None'}"},
                ],
                temperature=0.0,
                max_tokens=512,
            )
            return result.choices[0].message.content or thought
        except Exception as exc:
            logger.error("ToT synthesis failed: %s", exc)
            return thought

    def _score(self, thought: str, result: str) -> float:
        if not result or not result.strip():
            return 0.0
        base = min(1.0, len(result.split()) / 100.0)
        return max(0.0, min(1.0, base))

    def _select_best(self, node: ThoughtNode) -> ThoughtNode:
        if not node.children:
            return node
        best_child = max(node.children, key=lambda child: child.score)
        return self._select_best(best_child)
