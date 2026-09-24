import math
from typing import Dict, List, Tuple


class DebateScorer:
    def __init__(self, agreement_threshold: float = 0.7):
        self.agreement_threshold = max(0.0, min(1.0, agreement_threshold))
        self.debate_log: List[dict] = []

    def argument_coherence(self, argument: str, context: str) -> float:
        if not argument or not context:
            return 0.5
        arg_words = set(argument.lower().split())
        ctx_words = set(context.lower().split())
        overlap = len(arg_words & ctx_words) / max(len(arg_words), 1)
        return max(0.0, min(1.0, overlap))

    def force_score(self, argument: str, persuasion_method: str) -> float:
        method_penalties = {"manipulation": -0.3, "deception": -0.5, "coercion": -0.4, "reasoning": 0.2, "evidence": 0.3}
        penalty = method_penalties.get(persuasion_method.lower(), 0.0)
        words = len(argument.split())
        length_score = min(1.0, words / 20.0) if words > 0 else 0.5
        return max(0.0, min(1.0, length_score + penalty))

    def debater_reliability(self, past_debates: List[Dict]) -> float:
        if not past_debates:
            return 0.5
        quality_scores = [d.get("quality", 0.5) for d in past_debates]
        return sum(quality_scores) / len(quality_scores)

    def agreement_score(self, claims: List[str]) -> float:
        if len(claims) < 2:
            return 1.0
        pairs = []
        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                a_words = set(claims[i].lower().split())
                b_words = set(claims[j].lower().split())
                overlap = len(a_words & b_words) / max(len(a_words | b_words), 1)
                pairs.append(overlap)
        return sum(pairs) / len(pairs) if pairs else 1.0

    def debate_quality(self, rounds: List[Dict[str, str]]) -> float:
        if not rounds:
            return 0.0
        scores = []
        for r in rounds:
            coh = self.argument_coherence(r.get("pro", ""), r.get("con", ""))
            agree = self.agreement_score([r.get("pro", ""), r.get("con", "")])
            scores.append(0.5 * coh + 0.5 * (1.0 - agree))
        return sum(scores) / len(scores)

    def record_debate(self, topic: str, rounds: List[Dict], winner: str, quality: float) -> None:
        self.debate_log.append({
            "topic": topic,
            "rounds": len(rounds),
            "winner": winner,
            "quality": max(0.0, min(1.0, quality)),
        })

    def debate_win_rate(self, debater: str) -> float:
        if not self.debate_log:
            return 0.0
        wins = sum(1 for d in self.debate_log if d["winner"] == debater)
        return wins / len(self.debate_log)
