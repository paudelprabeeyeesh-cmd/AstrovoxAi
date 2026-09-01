"""Professional Engineering — ADRs, code review, project planning, risk assessment."""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ArchitectureDecisionRecord:
    """An Architecture Decision Record."""
    id: str
    title: str
    context: str
    decision: str
    consequences: str
    status: str = "accepted"
    created_at: float = 0.0

    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()


class ADRManager:
    """Manage Architecture Decision Records."""

    def __init__(self):
        self._adrs: dict[str, ArchitectureDecisionRecord] = {}

    def create(self, title: str, context: str, decision: str, consequences: str) -> ArchitectureDecisionRecord:
        """Create an ADR."""
        import secrets
        adr = ArchitectureDecisionRecord(
            id=secrets.token_hex(4),
            title=title,
            context=context,
            decision=decision,
            consequences=consequences,
        )
        self._adrs[adr.id] = adr
        return adr

    def get(self, adr_id: str) -> Optional[ArchitectureDecisionRecord]:
        """Get an ADR."""
        return self._adrs.get(adr_id)

    def list_adrs(self) -> list[ArchitectureDecisionRecord]:
        """List all ADRs."""
        return list(self._adrs.values())


@dataclass
class RiskAssessment:
    """A risk assessment."""
    id: str
    name: str
    likelihood: str
    impact: str
    mitigation: str
    status: str = "open"
    created_at: float = 0.0

    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()

    @property
    def risk_score(self) -> int:
        levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        return levels.get(self.likelihood, 1) * levels.get(self.impact, 1)


class RiskManager:
    """Manage project risks."""

    def __init__(self):
        self._risks: dict[str, RiskAssessment] = {}

    def add_risk(self, name: str, likelihood: str, impact: str, mitigation: str) -> RiskAssessment:
        """Add a risk."""
        import secrets
        risk = RiskAssessment(
            id=secrets.token_hex(4),
            name=name,
            likelihood=likelihood,
            impact=impact,
            mitigation=mitigation,
        )
        self._risks[risk.id] = risk
        return risk

    def get_risks_by_severity(self) -> dict:
        """Get risks grouped by severity."""
        high = []
        medium = []
        low = []

        for risk in self._risks.values():
            if risk.risk_score >= 6:
                high.append(risk)
            elif risk.risk_score >= 3:
                medium.append(risk)
            else:
                low.append(risk)

        return {"high": high, "medium": medium, "low": low}


adr_manager = ADRManager()
risk_manager = RiskManager()
