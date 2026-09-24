from typing import Any, Callable, Dict, List, Optional, Sequence


class CoordinationProtocol:
    def __init__(self, participants: Sequence[str]) -> None:
        self.participants = list(participants)
        self.state: Dict[str, Any] = {}
        self.phase: str = "idle"
        self.barrier_count: int = 0
        self.barrier_total: int = 0
        self.history: List[Dict[str, Any]] = []

    def propose(self, sender: str, proposal: Any) -> None:
        self.state[sender] = proposal
        self.history.append({"phase": self.phase, "sender": sender, "proposal": proposal})

    def start_barrier(self, total: int) -> None:
        self.barrier_total = total
        self.barrier_count = 0
        self.phase = "barrier"

    def arrive(self, sender: str) -> bool:
        if self.phase != "barrier":
            raise RuntimeError("Not in barrier phase")
        self.barrier_count += 1
        self.history.append({"phase": self.phase, "arrival": sender})
        return self.barrier_count >= self.barrier_total

    def release(self) -> None:
        self.phase = "released"
        self.history.append({"phase": self.phase})

    def snapshot(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "state": dict(self.state),
            "barrier_count": self.barrier_count,
            "barrier_total": self.barrier_total,
            "participants": list(self.participants),
        }
