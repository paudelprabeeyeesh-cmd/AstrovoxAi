"""Multi-agent debate system."""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Argument:
    agent_id: str
    text: str
    stance: str
    confidence: float
    evidence: list[str] = field(default_factory=list)


@dataclass
class DebateResult:
    debate_id: str
    topic: str
    rounds: int
    arguments: list[Argument]
    winner: Optional[str]
    consensus: Optional[str]


class DebateEngine:
    def __init__(self):
        self._debates: dict[str, DebateResult] = {}

    def start_debate(self, topic: str, agent_ids: list[str], rounds: int = 3) -> DebateResult:
        debate_id = str(uuid.uuid4())
        arguments: list[Argument] = []
        stances = {aid: "support" if i % 2 == 0 else "oppose" for i, aid in enumerate(agent_ids)}
        for round_num in range(rounds):
            for agent_id in agent_ids:
                argument = self._generate_argument(agent_id, topic, stances[agent_id], round_num)
                arguments.append(argument)
        winner = self._adjudicate(arguments)
        consensus = self._build_consensus(arguments) if winner else None
        result = DebateResult(
            debate_id=debate_id,
            topic=topic,
            rounds=rounds,
            arguments=arguments,
            winner=winner,
            consensus=consensus,
        )
        self._debates[debate_id] = result
        return result

    def _generate_argument(self, agent_id: str, topic: str, stance: str, round_num: int) -> Argument:
        return Argument(
            agent_id=agent_id,
            text=f"[{agent_id}] argues {stance} on round {round_num + 1}: {topic}",
            stance=stance,
            confidence=0.7 + (round_num * 0.05),
            evidence=[f"evidence-{agent_id}-{round_num}"],
        )

    def _adjudicate(self, arguments: list[Argument]) -> Optional[str]:
        if not arguments:
            return None
        scores: dict[str, float] = {}
        for arg in arguments:
            scores[arg.agent_id] = scores.get(arg.agent_id, 0.0) + arg.confidence
        if not scores:
            return None
        return max(scores, key=scores.get)

    def _build_consensus(self, arguments: list[Argument]) -> Optional[str]:
        supporting = [a for a in arguments if a.stance == "support"]
        if len(supporting) > len(arguments) / 2:
            return "consensus_support"
        return "no_clear_consensus"


debate_engine = DebateEngine()
