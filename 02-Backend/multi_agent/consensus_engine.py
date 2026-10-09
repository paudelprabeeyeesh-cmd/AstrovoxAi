from typing import Any, Callable, Dict, List, Optional, Sequence


class ConsensusEngine:
    def __init__(self, participants: Sequence[str]) -> None:
        self.participants = list(participants)
        self.votes: Dict[str, Any] = {}
        self.quorum: int = max(1, len(self.participants) // 2 + 1)
        self.decision: Optional[Any] = None
        self.rounds: int = 0
        self.history: List[Dict[str, Any]] = []

    def set_quorum(self, quorum: int) -> None:
        if quorum < 1:
            raise ValueError("Quorum must be at least 1")
        self.quorum = quorum

    def vote(self, voter: str, value: Any) -> None:
        self.votes[voter] = value
        self.history.append({"round": self.rounds, "voter": voter, "value": value})

    def tally(self) -> Optional[Any]:
        if len(self.votes) < self.quorum:
            return None
        counts: Dict[Any, int] = {}
        for value in self.votes.values():
            counts[value] = counts.get(value, 0) + 1
        best = max(counts.items(), key=lambda item: item[1])
        if best[1] > len(self.votes) / 2:
            self.decision = best[0]
            return self.decision
        self.rounds += 1
        self.history.append({"round": self.rounds, "action": "no_majority", "counts": dict(counts)})
        return None

    def reset(self) -> None:
        self.votes.clear()
        self.decision = None
        self.rounds = 0

    def summary(self) -> Dict[str, Any]:
        return {
            "participants": list(self.participants),
            "quorum": self.quorum,
            "votes_cast": len(self.votes),
            "decision": self.decision,
            "rounds": self.rounds,
        }
