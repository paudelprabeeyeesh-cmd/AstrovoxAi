"""Voting and consensus mechanisms."""

import logging
import uuid
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Vote:
    voter_id: str
    choice: str
    weight: float = 1.0
    reasoning: str = ""


@dataclass
class ConsensusResult:
    decision: str
    confidence: float
    dissenters: list[str]
    vote_counts: dict


class VotingEngine:
    def __init__(self):
        self._votes: dict[str, list[Vote]] = {}

    def collect_votes(self, proposal_id: str, voters: list[dict]) -> list[Vote]:
        votes = []
        for voter in voters:
            vote = Vote(
                voter_id=voter.get("id", str(uuid.uuid4())),
                choice=voter.get("choice", "abstain"),
                weight=float(voter.get("weight", 1.0)),
                reasoning=voter.get("reasoning", ""),
            )
            votes.append(vote)
        self._votes[proposal_id] = votes
        return votes

    def compute_consensus(self, proposal_id: str, method: str = "majority") -> ConsensusResult:
        votes = self._votes.get(proposal_id, [])
        if not votes:
            return ConsensusResult(decision="abstain", confidence=0.0, dissenters=[], vote_counts={})
        counts: dict[str, float] = {}
        for vote in votes:
            counts[vote.choice] = counts.get(vote.choice, 0.0) + vote.weight
        if method == "majority":
            decision = max(counts, key=counts.get)
            total = sum(counts.values())
            confidence = counts[decision] / total if total else 0.0
        elif method == "unanimous":
            decision = next(iter(counts)) if len(counts) == 1 else "blocked"
            confidence = 1.0 if len(counts) == 1 else 0.0
        else:
            decision = max(counts, key=counts.get)
            confidence = counts[decision] / sum(counts.values()) if sum(counts.values()) else 0.0
        dissenters = [v.voter_id for v in votes if v.choice != decision]
        return ConsensusResult(
            decision=decision,
            confidence=round(confidence, 3),
            dissenters=dissenters,
            vote_counts={k: round(v, 3) for k, v in counts.items()},
        )


voting_engine = VotingEngine()
