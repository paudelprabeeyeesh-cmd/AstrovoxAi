from dataclasses import dataclass, field
from typing import Dict, List, Optional
import random


@dataclass
class Offer:
    proposer: str
    terms: Dict[str, float]
    rationale: str = ""


@dataclass
class NegotiationState:
    parties: List[str]
    round: int = 0
    offers: List[Offer] = field(default_factory=list)
    concessions: Dict[str, float] = field(default_factory=dict)


class NegotiationEngine:
    def __init__(self, utility_weights: Optional[Dict[str, float]] = None, max_rounds: int = 20):
        self.utility_weights = utility_weights or {"price": 1.0, "time": 0.5, "quality": 0.8}
        self.max_rounds = max_rounds

    def propose(self, state: NegotiationState, proposer: str, terms: Dict[str, float], rationale: str = "") -> Offer:
        offer = Offer(proposer=proposer, terms=terms, rationale=rationale)
        state.offers.append(offer)
        state.round += 1
        return offer

    def evaluate(self, state: NegotiationState, perspective: str) -> float:
        if not state.offers:
            return 0.0
        latest = state.offers[-1]
        score = 0.0
        for key, weight in self.utility_weights.items():
            score += latest.terms.get(key, 0.0) * weight
        return score

    def counteroffer(self, state: NegotiationState, proposer: str, adjustments: Dict[str, float]) -> Optional[Offer]:
        if not state.offers:
            return None
        base = dict(state.offers[-1].terms)
        base.update(adjustments)
        return self.propose(state, proposer=proposer, terms=base, rationale="counteroffer")

    def concede(self, state: NegotiationState, party: str, item: str, amount: float) -> None:
        state.concessions[item] = state.concessions.get(item, 0.0) + amount

    def is_agreement(self, state: NegotiationState, threshold: float = 0.8) -> bool:
        if len(state.offers) < 2:
            return False
        last = state.offers[-1].terms
        prev = state.offers[-2].terms
        if not last or not prev:
            return False
        distance = sum(abs(last.get(k, 0.0) - prev.get(k, 0.0)) for k in set(last) | set(prev))
        return distance <= (1.0 - threshold)

    def get_summary(self, state: NegotiationState) -> Dict:
        return {
            "round": state.round,
            "offer_count": len(state.offers),
            "concessions": dict(state.concessions),
            "agreement": self.is_agreement(state),
        }
