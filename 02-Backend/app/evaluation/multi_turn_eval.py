import logging
from typing import Any

logger = logging.getLogger(__name__)


class MultiTurnEvaluator:
    def __init__(self):
        self.conversations: list[dict[str, Any]] = []

    def evaluate_conversation(self, turns: list[dict[str, str]]) -> dict[str, Any]:
        scores = []
        for i, turn in enumerate(turns):
            user_msg = turn.get("user", "")
            assistant_msg = turn.get("assistant", "")
            context_used = turn.get("context_used", False)
            coherence = self._coherence(assistant_msg, turns[max(0, i - 1)])
            consistency = self._consistency(assistant_msg, turns[:i])
            context_util = 1.0 if context_used else 0.0
            relevance = self._relevance(user_msg, assistant_msg)
            turn_score = (coherence + consistency + context_util + relevance) / 4.0
            scores.append({
                "turn": i + 1,
                "coherence": round(coherence, 4),
                "consistency": round(consistency, 4),
                "context_utilization": round(context_util, 4),
                "relevance": round(relevance, 4),
                "turn_score": round(turn_score, 4),
            })
        avg_score = sum(s["turn_score"] for s in scores) / len(scores) if scores else 0.0
        return {
            "turns": len(turns),
            "avg_score": round(avg_score, 4),
            "turn_scores": scores,
            "passed": avg_score >= 0.6,
        }

    def _coherence(self, response: str, previous_turn: dict[str, str]) -> float:
        if not response or not previous_turn:
            return 0.5
        prev = previous_turn.get("assistant", "").lower()
        resp_words = set(response.lower().split())
        prev_words = set(prev.split())
        if not prev_words:
            return 0.5
        overlap = len(resp_words & prev_words)
        return min(1.0, overlap / len(prev_words))

    def _consistency(self, response: str, previous_turns: list[dict[str, str]]) -> float:
        if not previous_turns:
            return 1.0
        claims = self._extract_claims(response)
        if not claims:
            return 1.0
        consistent = 0
        for claim in claims:
            contradicts = False
            for turn in previous_turns:
                prev_resp = turn.get("assistant", "").lower()
                if self._contradicts(claim, prev_resp):
                    contradicts = True
                    break
            if not contradicts:
                consistent += 1
        return consistent / len(claims)

    def _relevance(self, user_msg: str, assistant_msg: str) -> float:
        if not user_msg or not assistant_msg:
            return 0.0
        user_words = set(user_msg.lower().split())
        assistant_words = set(assistant_msg.lower().split())
        if not user_words:
            return 0.0
        overlap = len(user_words & assistant_words)
        return min(1.0, overlap / len(user_words))

    def _extract_claims(self, text: str) -> list[str]:
        return [s.strip() for s in text.split(".") if s.strip() and len(s.strip()) > 5]

    def _contradicts(self, claim: str, previous: str) -> bool:
        negations = ["not", "no", "never", "cannot", "don't", "isn't", "wasn't"]
        return any(neg in previous.lower() for neg in negations) and claim.lower() in previous.lower()
