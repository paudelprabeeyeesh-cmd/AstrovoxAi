import math
import heapq
import time
from dataclasses import dataclass, field
from typing import Any

from .iit import IntegratedInformationTheory, IITState


@dataclass
class BroadcastMessage:
    content: Any
    source: str
    timestamp: float = field(default_factory=time.time)
    urgency: float = 0.5
    attention_weight: float = 0.0
    module_origin: str = "unknown"


class GlobalWorkspaceTheory:
    def __init__(self, capacity: int = 7):
        self.capacity = capacity
        self.workspace: list[BroadcastMessage] = []
        self.competition_history: list[dict[str, Any]] = []
        self.iit = IntegratedInformationTheory()
        self.conscious_threshold = 0.4

    def compete_for_access(self, candidates: list[BroadcastMessage]) -> BroadcastMessage | None:
        scored = []
        for candidate in candidates:
            score = self._score_candidate(candidate)
            scored.append((score, candidate))
        scored.sort(key=lambda x: x[0], reverse=True)
        if not scored:
            return None
        winner = scored[0][1]
        self.workspace = [winner] + [m for _, m in scored[1 : self.capacity]]
        self.competition_history.append(
            {
                "timestamp": time.time(),
                "winner": winner.source,
                "candidates": len(candidates),
                "winner_score": scored[0][0],
            }
        )
        return winner

    def _score_candidate(self, candidate: BroadcastMessage) -> float:
        base = candidate.urgency * 0.4 + candidate.attention_weight * 0.4
        iit_state = self.iit.compute_full_iit_state()
        consciousness_boost = iit_state.phi * 0.2
        return base + consciousness_boost

    def broadcast(self, message: BroadcastMessage):
        self.workspace.append(message)
        if len(self.workspace) > self.capacity:
            self.workspace = sorted(
                self.workspace,
                key=lambda m: m.attention_weight + m.urgency,
                reverse=True,
            )[: self.capacity]

    def get_conscious_contents(self) -> list[BroadcastMessage]:
        contents = []
        for msg in self.workspace:
            iit_state = self.iit.compute_full_iit_state()
            if iit_state.phi > self.conscious_threshold:
                contents.append(msg)
        return contents

    def integrate_and_broadcast(self, modules: dict[str, Any]) -> BroadcastMessage | None:
        candidates = []
        for module_name, module in modules.items():
            if hasattr(module, "generate_candidate"):
                try:
                    candidate = module.generate_candidate()
                    candidates.append(candidate)
                except Exception:
                    continue
        if not candidates:
            return None
        winner = self.compete_for_access(candidates)
        if winner:
            self.broadcast(winner)
        return winner
