from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MoralAccountability:
    action_id: str
    agent_id: str
    consequences: list[str]
    responsibility_score: float
    mitigating_factors: list[str] = field(default_factory=list)
    aggravating_factors: list[str] = field(default_factory=list)
    affected_parties: list[str] = field(default_factory=list)
    restitution_required: bool = False
    restitution_actions: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class MoralResponsibilityTracker:
    def __init__(self):
        self.accounts: dict[str, MoralAccountability] = {}
        self.agent_responsibility: dict[str, float] = {}
        self.transfer_rules: list[dict[str, Any]] = []
        self.agent_capability_profiles: dict[str, dict[str, float]] = {}
        self.justification_log: list[dict[str, Any]] = []
        self.remedy_registry: dict[str, list[str]] = {}

    def record_action(self, action_id: str, agent_id: str, consequences: list[str], context: dict[str, Any] | None = None) -> MoralAccountability:
        ctx = context or {}
        mitigating = ctx.get("mitigating_factors", [])
        aggravating = ctx.get("aggravating_factors", [])
        affected = ctx.get("affected_parties", ["unknown"])
        responsibility = self._compute_responsibility(agent_id, consequences, mitigating, aggravating)
        restitution = self._assess_restitution_needed(consequences, responsibility)
        actions = self._generate_restitution_actions(consequences, affected)
        account = MoralAccountability(
            action_id=action_id,
            agent_id=agent_id,
            consequences=consequences,
            responsibility_score=responsibility,
            mitigating_factors=mitigating,
            aggravating_factors=aggravating,
            affected_parties=affected,
            restitution_required=restitution,
            restitution_actions=actions,
        )
        self.accounts[action_id] = account
        self.agent_responsibility[agent_id] = self.agent_responsibility.get(agent_id, 0.0) + responsibility
        self.justification_log.append({
            "action_id": action_id,
            "agent_id": agent_id,
            "responsibility": responsibility,
            "mitigating": mitigating,
            "aggravating": aggravating,
            "timestamp": datetime.now().isoformat(),
        })
        return account

    def transfer_responsibility(self, from_agent: str, to_agent: str, action_id: str, transfer_reason: str) -> bool:
        if action_id not in self.accounts:
            return False
        account = self.accounts[action_id]
        if account.agent_id != from_agent:
            return False
        transferred_amount = account.responsibility_score * 0.5
        account.agent_id = to_agent
        self.agent_responsibility[from_agent] = max(0.0, self.agent_responsibility.get(from_agent, 0.0) - transferred_amount)
        self.agent_responsibility[to_agent] = self.agent_responsibility.get(to_agent, 0.0) + transferred_amount
        self.transfer_rules.append({
            "from": from_agent,
            "to": to_agent,
            "action_id": action_id,
            "reason": transfer_reason,
            "amount": transferred_amount,
            "timestamp": datetime.now().isoformat(),
        })
        return True

    def get_agent_report(self, agent_id: str) -> dict[str, Any]:
        agent_accounts = [a for a in self.accounts.values() if a.agent_id == agent_id]
        restitution_count = sum(1 for a in agent_accounts if a.restitution_required)
        return {
            "agent_id": agent_id,
            "total_responsibility": round(self.agent_responsibility.get(agent_id, 0.0), 4),
            "account_count": len(agent_accounts),
            "restitution_required_count": restitution_count,
            "recent_actions": [
                {
                    "action_id": a.action_id,
                    "responsibility": round(a.responsibility_score, 4),
                    "consequences": a.consequences[:3],
                }
                for a in agent_accounts[-5:]
            ],
        }

    def get_system_report(self) -> dict[str, Any]:
        return {
            "total_accounts": len(self.accounts),
            "total_agents": len(self.agent_responsibility),
            "total_responsibility_tracked": round(sum(self.agent_responsibility.values()), 4),
            "transfers_recorded": len(self.transfer_rules),
            "justifications_logged": len(self.justification_log),
            "top_agents_by_responsibility": sorted(
                self.agent_responsibility.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }

    def _compute_responsibility(self, agent_id: str, consequences: list[str], mitigating: list[str], aggravating: list[str]) -> float:
        base = 0.5
        if len(consequences) > 3:
            base += 0.2
        if "harm" in " ".join(consequences).lower():
            base += 0.3
        for factor in mitigating:
            base -= 0.08
        for factor in aggravating:
            base += 0.1
        capability = self.agent_capability_profiles.get(agent_id, {}).get("autonomy", 0.7)
        base *= capability
        return max(0.0, min(1.0, base))

    def _assess_restitution_needed(self, consequences: list[str], responsibility: float) -> bool:
        harm_keywords = ["harm", "damage", "loss", "injury", "death", "destruction"]
        text = " ".join(consequences).lower()
        harm_score = sum(1 for kw in harm_keywords if kw in text)
        return responsibility > 0.5 and harm_score > 0

    def _generate_restitution_actions(self, consequences: list[str], affected: list[str]) -> list[str]:
        actions = []
        text = " ".join(consequences).lower()
        if "harm" in text:
            actions.append("Compensate affected parties")
        if "damage" in text:
            actions.append("Repair or replace damaged assets")
        if "loss" in text:
            actions.append("Provide restitution for losses")
        if not actions:
            actions.append("Issue formal apology")
        return actions
