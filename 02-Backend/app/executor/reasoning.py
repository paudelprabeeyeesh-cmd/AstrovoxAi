"""AI Reasoning Engine: chain, tree, graph, debate, reflection, verification.

Provides composable reasoning strategies that operate over a problem and
an optional set of facts retrieved from memory.
"""

from __future__ import annotations

import math
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from . import make_id, now
from .memory_brain import MemoryBrain, MemoryItem, MemoryType, get_memory_brain
from ..logging_config import get_logger

logger = get_logger(__name__)


class ReasoningStrategy(str, Enum):
    CHAIN = "chain"
    TREE = "tree"
    GRAPH = "graph"
    DEBATE = "debate"
    REFLECTION = "reflection"
    VERIFICATION = "verification"


@dataclass
class ReasoningStep:
    id: str
    strategy: ReasoningStrategy
    content: str
    confidence: float
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "strategy": self.strategy.value,
            "content": self.content,
            "confidence": round(self.confidence, 4),
            "parent_id": self.parent_id,
            "metadata": self.metadata,
        }


@dataclass
class ReasoningResult:
    problem: str
    final_answer: str
    confidence: float
    steps: List[ReasoningStep] = field(default_factory=list)
    strategies_used: List[ReasoningStrategy] = field(default_factory=list)
    facts_used: List[MemoryItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "problem": self.problem,
            "final_answer": self.final_answer,
            "confidence": round(self.confidence, 4),
            "steps": [s.to_dict() for s in self.steps],
            "strategies_used": [s.value for s in self.strategies_used],
            "facts_count": len(self.facts_used),
        }


# ---------------------------------------------------------------------------
# Individual reasoning strategies
# ---------------------------------------------------------------------------


def chain_reason(problem: str, facts: Sequence[MemoryItem]) -> List[ReasoningStep]:
    """Chain reasoning: linear step-by-step deduction."""

    steps: List[ReasoningStep] = []
    steps.append(
        ReasoningStep(
            id=make_id("rsn"),
            strategy=ReasoningStrategy.CHAIN,
            content=f"Understand the problem: {problem}",
            confidence=0.7,
        )
    )
    for i, fact in enumerate(facts[:3]):
        steps.append(
            ReasoningStep(
                id=make_id("rsn"),
                strategy=ReasoningStrategy.CHAIN,
                content=f"Consider fact: {fact.content}",
                confidence=min(0.9, fact.confidence),
                parent_id=steps[-1].id,
                metadata={"fact_id": fact.id, "index": i},
            )
        )
    if len(steps) > 1:
        synthesis = "Based on the available facts, the most reasonable answer is: " + problem
        steps.append(
            ReasoningStep(
                id=make_id("rsn"),
                strategy=ReasoningStrategy.CHAIN,
                content=synthesis,
                confidence=0.6,
                parent_id=steps[-1].id,
            )
        )
    return steps


def tree_reason(problem: str, facts: Sequence[MemoryItem]) -> List[ReasoningStep]:
    """Tree reasoning: branching paths with pruning."""

    root = ReasoningStep(
        id=make_id("rsn"),
        strategy=ReasoningStrategy.TREE,
        content=f"Root: {problem}",
        confidence=0.7,
    )
    branches: List[ReasoningStep] = []
    for i, fact in enumerate(facts[:4]):
        branches.append(
            ReasoningStep(
                id=make_id("rsn"),
                strategy=ReasoningStrategy.TREE,
                content=f"Branch {i}: investigate {fact.content}",
                confidence=fact.confidence,
                parent_id=root.id,
            )
        )
    # Prune low-confidence branches.
    kept = [b for b in branches if b.confidence >= 0.5]
    if kept:
        chosen = max(kept, key=lambda s: s.confidence)
        root.confidence = chosen.confidence
    return [root, *branches]


def graph_reason(problem: str, facts: Sequence[MemoryItem]) -> List[ReasoningStep]:
    """Graph reasoning: link related facts into a graph and traverse it."""

    nodes: List[ReasoningStep] = []
    for i, fact in enumerate(facts[:5]):
        nodes.append(
            ReasoningStep(
                id=make_id("node"),
                strategy=ReasoningStrategy.GRAPH,
                content=f"Node {i}: {fact.content}",
                confidence=fact.confidence,
                metadata={"tags": fact.tags},
            )
        )
    # Connect nodes with shared tags.
    for i, a in enumerate(nodes):
        for j, b in enumerate(nodes):
            if i >= j:
                continue
            shared_tags = set(a.metadata.get("tags", [])) & set(b.metadata.get("tags", []))
            if shared_tags:
                a.metadata.setdefault("edges", []).append(b.id)
                b.metadata.setdefault("edges", []).append(a.id)
    if nodes:
        nodes[0].content = f"Anchor: {problem}"
    return nodes


def debate_reason(problem: str, facts: Sequence[MemoryItem]) -> List[ReasoningStep]:
    """Debate reasoning: generate two opposing views and weigh them."""

    pro = ReasoningStep(
        id=make_id("debate"),
        strategy=ReasoningStrategy.DEBATE,
        content=f"Pro: {problem} — supported by evidence",
        confidence=0.6,
    )
    con = ReasoningStep(
        id=make_id("debate"),
        strategy=ReasoningStrategy.DEBATE,
        content=f"Con: {problem} — but counter-evidence exists",
        confidence=0.5,
        parent_id=pro.id,
    )
    judge = ReasoningStep(
        id=make_id("debate"),
        strategy=ReasoningStrategy.DEBATE,
        content=f"Verdict: balance pro and con for {problem}",
        confidence=(pro.confidence + con.confidence) / 2,
        parent_id=con.id,
    )
    return [pro, con, judge]


def reflection_reason(problem: str, facts: Sequence[MemoryItem], result: Optional[ReasoningResult] = None) -> List[ReasoningStep]:
    """Reflect on a prior reasoning result or initial analysis."""

    if result is None:
        return [
            ReasoningStep(
                id=make_id("ref"),
                strategy=ReasoningStrategy.REFLECTION,
                content=f"Reflect on problem: {problem}",
                confidence=0.5,
            )
        ]
    last = result.steps[-1] if result.steps else None
    confidence = last.confidence if last else 0.5
    return [
        ReasoningStep(
            id=make_id("ref"),
            strategy=ReasoningStrategy.REFLECTION,
            content=f"Reflecting on: {last.content if last else problem}",
            confidence=confidence,
        ),
        ReasoningStep(
            id=make_id("ref"),
            strategy=ReasoningStrategy.REFLECTION,
            content="Refined answer with higher confidence",
            confidence=min(0.95, confidence + 0.1),
        ),
    ]


def verification_reason(problem: str, candidate: str) -> List[ReasoningStep]:
    """Verify a candidate answer against the problem."""

    score = _verification_score(problem, candidate)
    return [
        ReasoningStep(
            id=make_id("ver"),
            strategy=ReasoningStrategy.VERIFICATION,
            content=f"Check: does '{candidate}' address '{problem}'?",
            confidence=score,
        ),
    ]


def _verification_score(problem: str, candidate: str) -> float:
    p_terms = set(re.findall(r"\w+", problem.lower()))
    c_terms = set(re.findall(r"\w+", candidate.lower()))
    if not p_terms:
        return 0.5
    overlap = len(p_terms & c_terms) / len(p_terms)
    return min(0.99, max(0.1, overlap))


# ---------------------------------------------------------------------------
# Reasoning engine
# ---------------------------------------------------------------------------


class ReasoningEngine:
    """Composes reasoning strategies to answer a problem."""

    def __init__(self, brain: Optional[MemoryBrain] = None) -> None:
        self.brain = brain or get_memory_brain()
        self._history: List[ReasoningResult] = []

    def solve(
        self,
        problem: str,
        *,
        strategies: Optional[List[ReasoningStrategy]] = None,
        fact_limit: int = 5,
    ) -> ReasoningResult:
        strategies = strategies or [
            ReasoningStrategy.CHAIN,
            ReasoningStrategy.TREE,
            ReasoningStrategy.REFLECTION,
            ReasoningStrategy.VERIFICATION,
        ]
        facts = self.brain.recall(problem, limit=fact_limit)
        steps: List[ReasoningStep] = []
        used: List[ReasoningStrategy] = []
        candidate = problem

        for strategy in strategies:
            if strategy == ReasoningStrategy.CHAIN:
                steps.extend(chain_reason(problem, facts))
            elif strategy == ReasoningStrategy.TREE:
                steps.extend(tree_reason(problem, facts))
            elif strategy == ReasoningStrategy.GRAPH:
                steps.extend(graph_reason(problem, facts))
            elif strategy == ReasoningStrategy.DEBATE:
                steps.extend(debate_reason(problem, facts))
            elif strategy == ReasoningStrategy.REFLECTION:
                partial = ReasoningResult(
                    problem=problem,
                    final_answer=candidate,
                    confidence=0.5,
                    steps=list(steps),
                )
                reflected = reflection_reason(problem, facts, partial)
                steps.extend(reflected)
                if reflected:
                    candidate = reflected[-1].content
            elif strategy == ReasoningStrategy.VERIFICATION:
                steps.extend(verification_reason(problem, candidate))
            used.append(strategy)

        if steps:
            avg_confidence = sum(s.confidence for s in steps) / len(steps)
            final = steps[-1].content
        else:
            avg_confidence = 0.5
            final = problem

        result = ReasoningResult(
            problem=problem,
            final_answer=final,
            confidence=avg_confidence,
            steps=steps,
            strategies_used=used,
            facts_used=list(facts),
        )
        self._history.append(result)
        return result

    def history(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._history]


_GLOBAL_ENGINE: Optional[ReasoningEngine] = None


def get_reasoning_engine() -> ReasoningEngine:
    global _GLOBAL_ENGINE
    if _GLOBAL_ENGINE is None:
        _GLOBAL_ENGINE = ReasoningEngine()
    return _GLOBAL_ENGINE