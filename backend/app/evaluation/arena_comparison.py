"""Arena comparison for side-by-side model evaluation."""
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class ArenaMatch:
    match_id: str
    model_a: str
    model_b: str
    prompt: str
    response_a: str
    response_b: str
    winner: str
    judge: str = "auto"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ArenaResult:
    model: str
    wins: int
    losses: int
    ties: int
    elo: float = 1000.0


class ArenaComparison:
    def __init__(self):
        self._matches: List[ArenaMatch] = []
        self._ratings: Dict[str, ArenaResult] = {}

    def record_match(
        self,
        match_id: str,
        model_a: str,
        model_b: str,
        prompt: str,
        response_a: str,
        response_b: str,
        winner: str,
        judge: str = "auto",
    ) -> ArenaMatch:
        match = ArenaMatch(
            match_id=match_id,
            model_a=model_a,
            model_b=model_b,
            prompt=prompt,
            response_a=response_a,
            response_b=response_b,
            winner=winner,
            judge=judge,
        )
        self._matches.append(match)
        self._update_ratings(match)
        logger.info("Arena match %s: %s vs %s -> %s", match_id, model_a, model_b, winner)
        return match

    def _update_ratings(self, match: ArenaMatch) -> None:
        for model in (match.model_a, match.model_b):
            if model not in self._ratings:
                self._ratings[model] = ArenaResult(model=model, wins=0, losses=0, ties=0)

        ra = self._ratings[match.model_a]
        rb = self._ratings[match.model_b]

        if match.winner == match.model_a:
            ra.wins += 1
            rb.losses += 1
        elif match.winner == match.model_b:
            rb.wins += 1
            ra.losses += 1
        else:
            ra.ties += 1
            rb.ties += 1

        expected_a = 1.0 / (1.0 + 10 ** ((rb.elo - ra.elo) / 400.0))
        expected_b = 1.0 / (1.0 + 10 ** ((ra.elo - rb.elo) / 400.0))
        k = 32.0
        if match.winner == match.model_a:
            sa, sb = 1.0, 0.0
        elif match.winner == match.model_b:
            sa, sb = 0.0, 1.0
        else:
            sa, sb = 0.5, 0.5
        ra.elo = ra.elo + k * (sa - expected_a)
        rb.elo = rb.elo + k * (sb - expected_b)

    def run_batch(self, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = []
        for m in matches:
            start = time.time()
            result = self.record_match(
                match_id=m["match_id"],
                model_a=m["model_a"],
                model_b=m["model_b"],
                prompt=m.get("prompt", ""),
                response_a=m.get("response_a", ""),
                response_b=m.get("response_b", ""),
                winner=m.get("winner", m["model_a"]),
                judge=m.get("judge", "auto"),
            )
            results.append(result)
        return self._summarize()

    def _summarize(self) -> Dict[str, Any]:
        return {
            "matches": len(self._matches),
            "models": [
                {
                    "model": model,
                    "wins": r.wins,
                    "losses": r.losses,
                    "ties": r.ties,
                    "elo": round(r.elo, 2),
                }
                for model, r in sorted(self._ratings.items(), key=lambda x: x[1].elo, reverse=True)
            ],
        }

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        return self._summarize()["models"]

    def get_matches(self) -> List[Dict[str, Any]]:
        return [m.__dict__ for m in self._matches]
