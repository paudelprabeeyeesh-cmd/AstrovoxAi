import numpy as np
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple


@dataclass
class DebateRound:
    round_number: int
    proponent_argument: str
    critic_argument: str
    winner: Optional[str]
    confidence: float


@dataclass
class RRMResult:
    base_reward: float
    critique_score: float
    final_reward: float
    improved: bool


class DebateFramework:
    def __init__(self, max_rounds: int = 3, judge: Optional[Callable] = None):
        self.max_rounds = max_rounds
        self.judge = judge or self._default_judge
        self.history: List[DebateRound] = []

    def _default_judge(self, proponent: str, critic: str) -> Tuple[str, float]:
        pro = len(proponent)
        crit = len(critic)
        if pro > crit:
            return "proponent", 0.7
        elif crit > pro:
            return "critic", 0.6
        return "draw", 0.5

    def run_debate(self, question: str, proponent_fn: Callable, critic_fn: Callable) -> DebateRound:
        proponent_arg = proponent_fn(question)
        critic_arg = critic_fn(question)
        winner, confidence = self.judge(proponent_arg, critic_arg)
        round_ = DebateRound(
            round_number=len(self.history) + 1,
            proponent_argument=proponent_arg,
            critic_argument=critic_arg,
            winner=winner,
            confidence=round(confidence, 4),
        )
        self.history.append(round_)
        return round_

    def get_debate_summary(self) -> Dict:
        if not self.history:
            return {"rounds": 0, "proponent_wins": 0, "critic_wins": 0, "draws": 0}
        proponent_wins = sum(1 for r in self.history if r.winner == "proponent")
        critic_wins = sum(1 for r in self.history if r.winner == "critic")
        draws = sum(1 for r in self.history if r.winner == "draw")
        return {
            "rounds": len(self.history),
            "proponent_wins": proponent_wins,
            "critic_wins": critic_wins,
            "draws": draws,
            "avg_confidence": round(np.mean([r.confidence for r in self.history]), 4),
        }


class RecursiveRewardModel:
    def __init__(self, num_self_critiques: int = 3):
        self.num_self_critiques = num_self_critiques
        self.reward_history: List[RRMResult] = []

    def critique(self, output: str) -> str:
        critiques = []
        for i in range(self.num_self_critiques):
            critique = f"critique_{i}: check_accuracy_{i}"
            critiques.append(critique)
        return " | ".join(critiques)

    def compute_reward(self, base_reward: float, output: str) -> RRMResult:
        critique_text = self.critique(output)
        critique_score = min(len(critique_text) / 200.0, 1.0)
        noise = np.random.RandomState(abs(hash(output)) % (2**32)).uniform(-0.05, 0.05)
        critique_score = np.clip(critique_score + noise, 0.0, 1.0)
        final_reward = base_reward * 0.7 + critique_score * 0.3
        improved = bool((final_reward > base_reward).item())
        result = RRMResult(
            base_reward=round(base_reward, 4),
            critique_score=round(critique_score, 4),
            final_reward=round(final_reward, 4),
            improved=improved,
        )
        self.reward_history.append(result)
        return result

    def get_training_stats(self) -> Dict:
        if not self.reward_history:
            return {"total": 0, "improved_rate": 0.0, "avg_base_reward": 0.0, "avg_final_reward": 0.0}
        total = len(self.reward_history)
        improved = sum(1 for r in self.reward_history if r.improved)
        return {
            "total": total,
            "improved_rate": round(improved / total, 4),
            "avg_base_reward": round(np.mean([r.base_reward for r in self.reward_history]), 4),
            "avg_final_reward": round(np.mean([r.final_reward for r in self.reward_history]), 4),
        }
