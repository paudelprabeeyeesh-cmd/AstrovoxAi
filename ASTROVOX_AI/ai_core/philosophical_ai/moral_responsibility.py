from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MoralAccountability:
    action_id: str
    agent_id: str
    consequences: list[str]
    responsibility_score: float
    timestamp: datetime = field(default_factory=datetime.now)


class MoralResponsibilityTracker:
    def __init__(self):
        self.accounts: dict[str, MoralAccountability] = {}
        self.agent_responsibility: dict[str, float] = {}
        self.transfer_rules: list[dict[str, Any]] = []

    def record_action(self, action_id: str, agent_id: str, consequences: list[str]) -> MoralAccountability:
        responsibility = self._compute_responsibility(agent_id, consequences)
        account = MoralAccountability(
            action_id=action_id,
            agent_id=agent_id,
            consequences=consequences,
            responsibility_score=responsibility,
        )
        self.accounts[action_id] = account
        self.agent_responsibility[agent_id] = self.agent_responsibility.get(agent_id, 0.0) + responsibility
        return account

    def _compute_responsibility(self, agent_id: str, consequences: list[str]) -> float:
        base = 0.5
        if len(consequences) > 3:
            base += 0.2
        if "harm" in " ".join(consequences).lower():
            base += 0.3
        return min(1.0, base)

    def get_agent_report(self, agent_id: str) -> dict[str, Any]:
        return {
            "agent_id": agent_id,
            "total_responsibility": self.agent_responsibility.get(agent_id, 0.0),
            "account_count": sum(1 for a in self.accounts.values() if a.agent_id == agent_id),
        }
