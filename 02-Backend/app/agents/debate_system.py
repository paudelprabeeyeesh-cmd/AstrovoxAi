"""Multi-agent debate system with consensus and scoring."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class DebateRound(Enum):
    OPENING = "opening"
    REBUTTAL = "rebuttal"
    CROSS_EXAMINATION = "cross_examination"
    CLOSING = "closing"
    CONSENSUS = "consensus"


@dataclass
class DebateArgument:
    agent_id: str
    round: DebateRound
    content: str
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DebateResult:
    debate_id: str
    topic: str
    winner: Optional[str]
    consensus: Optional[str]
    arguments: List[DebateArgument]
    scores: Dict[str, float]
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MultiAgentDebateSystem:
    """Coordinate structured debates between multiple agents."""

    def __init__(self):
        self._debates: Dict[str, DebateResult] = {}
        self._agents: Dict[str, Callable] = {}

    def register_agent(self, agent_id: str, handler: Callable) -> None:
        self._agents[agent_id] = handler

    async def run_debate(
        self,
        debate_id: str,
        topic: str,
        agent_ids: List[str],
        rounds: List[DebateRound] = None,
    ) -> DebateResult:
        if rounds is None:
            rounds = [
                DebateRound.OPENING,
                DebateRound.REBUTTAL,
                DebateRound.CONSENSUS,
            ]
        arguments: List[DebateArgument] = []
        scores: Dict[str, float] = {aid: 0.0 for aid in agent_ids}

        for round_type in rounds:
            for agent_id in agent_ids:
                handler = self._agents.get(agent_id)
                if not handler:
                    continue
                try:
                    if asyncio.iscoroutinefunction(handler):
                        content = await handler(topic, round_type)
                    else:
                        content = handler(topic, round_type)
                    arg = DebateArgument(
                        agent_id=agent_id,
                        round=round_type,
                        content=str(content),
                    )
                    arguments.append(arg)
                    scores[agent_id] += self._score_argument(arg)
                except Exception as exc:
                    logger.warning("Debate agent %s failed: %s", agent_id, exc)

        winner = max(scores, key=scores.get) if scores else None
        consensus = self._build_consensus(arguments)
        result = DebateResult(
            debate_id=debate_id,
            topic=topic,
            winner=winner,
            consensus=consensus,
            arguments=arguments,
            scores=scores,
        )
        self._debates[debate_id] = result
        return result

    def _score_argument(self, argument: DebateArgument) -> float:
        base = min(len(argument.content) / 500.0, 1.0)
        evidence_bonus = min(len(argument.evidence) * 0.1, 0.3)
        return max(0.0, min(1.0, base + evidence_bonus)) * argument.confidence

    def _build_consensus(self, arguments: List[DebateArgument]) -> Optional[str]:
        if not arguments:
            return None
        closing = [a for a in arguments if a.round == DebateRound.CLOSING]
        if closing:
            return closing[-1].content
        return arguments[-1].content

    def get_result(self, debate_id: str) -> Optional[DebateResult]:
        return self._debates.get(debate_id)


import asyncio
