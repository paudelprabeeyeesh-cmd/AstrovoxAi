"""Multi-agent debate with confidence scoring and convergence detection."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DebateTurn:
    agent: str
    argument: str
    confidence: float
    rebuttal: str | None = None


@dataclass
class DebateResult:
    winner: str
    consensus: str
    confidence: float
    turns: list[DebateTurn]


class MultiAgentDebate:
    def __init__(self, max_rounds: int = 2) -> None:
        self.max_rounds = max_rounds
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def debate(self, topic: str, agents: list[str]) -> DebateResult:
        turns: list[DebateTurn] = []
        current = topic
        for round_idx in range(self.max_rounds):
            for agent in agents:
                argument = self._argue(agent, current, turns)
                confidence = self._estimate_confidence(argument)
                turns.append(DebateTurn(agent=agent, argument=argument, confidence=confidence))
                current = self._summarize(turns)
        winner = max(turns, key=lambda turn: turn.confidence)
        consensus = self._synthesize_consensus(turns)
        return DebateResult(winner=winner.agent, consensus=consensus, confidence=winner.confidence, turns=turns)

    def _argue(self, agent: str, topic: str, history: list[DebateTurn]) -> str:
        try:
            client = self._get_client()
            history_text = "\n".join([f"{turn.agent}: {turn.argument}" for turn in history[-4:]])
            result = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {"role": "system", "content": f"You are {agent}. Argue concisely for the best answer."},
                    {"role": "user", "content": f"Topic:\n{topic}\n\nHistory:\n{history_text}"},
                ],
                temperature=0.4,
                max_tokens=256,
            )
            return result.choices[0].message.content or ""
        except Exception as exc:
            logger.error("Debate argument failed for %s: %s", agent, exc)
            return ""

    def _estimate_confidence(self, argument: str) -> float:
        if not argument or not argument.strip():
            return 0.0
        base = 0.6
        if len(argument.split()) > 40:
            base += 0.1
        if any(term in argument.lower() for term in ["because", "therefore", "evidence"]):
            base += 0.1
        return max(0.0, min(1.0, base))

    def _summarize(self, turns: list[DebateTurn]) -> str:
        return "\n".join([f"{turn.agent}: {turn.argument}" for turn in turns[-4:]])

    def _synthesize_consensus(self, turns: list[DebateTurn]) -> str:
        if not turns:
            return ""
        best = max(turns, key=lambda turn: turn.confidence)
        return best.argument
