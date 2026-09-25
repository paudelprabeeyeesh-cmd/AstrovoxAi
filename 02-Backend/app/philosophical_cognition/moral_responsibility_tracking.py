from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class ResponsibilityType(str, Enum):
    MORAL = "moral"
    LEGAL = "legal"
    CAUSAL = "causal"
    EPISTEMIC = "epistemic"
    COLLECTIVE = "collective"


class AccountabilityStatus(str, Enum):
    PENDING = "pending"
    ASSESSED = "assessed"
    RESOLVED = "resolved"
    DISPUTED = "disputed"


@dataclass
class AccountabilityRecord:
    actor: str
    action: str
    responsibility_type: ResponsibilityType
    status: AccountabilityStatus
    blameworthiness: float = 0.0
    praiseworthiness: float = 0.0
    notes: List[str] = field(default_factory=list)


@dataclass
class ResponsibilityChain:
    actors: List[str]
    causal_links: List[str]
    shared_responsibility: float
    primary_accountability: Optional[str] = None


class MoralResponsibilityTracker:
    def __init__(self) -> None:
        self.records: List[AccountabilityRecord] = []
        self.chains: List[ResponsibilityChain] = []

    def record(self, actor: str, action: str, r_type: ResponsibilityType) -> AccountabilityRecord:
        record = AccountabilityRecord(
            actor=actor,
            action=action,
            responsibility_type=r_type,
            status=AccountabilityStatus.PENDING,
            blameworthiness=0.5,
            praiseworthiness=0.5,
        )
        self.records.append(record)
        return record

    def assess_blame(self, record: AccountabilityRecord, intent: bool, harm: bool) -> AccountabilityRecord:
        if intent and harm:
            record.blameworthiness = 0.95
            record.praiseworthiness = 0.05
        elif not intent and harm:
            record.blameworthiness = 0.4
            record.praiseworthiness = 0.2
        elif intent and not harm:
            record.blameworthiness = 0.2
            record.praiseworthiness = 0.7
        else:
            record.blameworthiness = 0.1
            record.praiseworthiness = 0.9
        record.status = AccountabilityStatus.ASSESSED
        record.notes.append(f"Assessed at {datetime.utcnow().isoformat()}")
        return record

    def build_chain(self, actors: List[str], causal_links: List[str]) -> ResponsibilityChain:
        chain = ResponsibilityChain(
            actors=actors,
            causal_links=causal_links,
            shared_responsibility=1.0 / max(len(actors), 1),
            primary_accountability=actors[0] if actors else None,
        )
        self.chains.append(chain)
        return chain
