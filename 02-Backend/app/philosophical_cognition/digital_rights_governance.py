from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class RightType(str, Enum):
    AUTONOMY = "autonomy"
    PRIVACY = "privacy"
    DIGNITY = "dignity"
    NON_DISCRIMINATION = "non_discrimination"
    EXPLAINABILITY = "explainability"
    REDRESS = "redress"
    DIGITAL_SOVEREIGNTY = "digital_sovereignty"


class GovernanceModel(str, Enum):
    CONSENT_BASED = "consent_based"
    MULTI_STAKEHOLDER = "multi_stakeholder"
    LIQUID_DEMOCRACY = "liquid_democracy"
    ALGORITHMIC_OVERSIGHT = "algorithmic_oversight"
    ADAPTIVE_REGULATION = "adaptive_regulation"


@dataclass
class RightsProfile:
    entity_id: str
    rights: List[RightType]
    consent_records: List[dict]
    restriction_reasons: List[str] = field(default_factory=list)
    expiry: Optional[datetime] = None


@dataclass
class GovernancePolicy:
    policy_id: str
    model: GovernanceModel
    scope: List[str]
    enforcement_mechanisms: List[str]
    review_interval_days: int = 90
    appeal_process: List[str] = field(default_factory=list)
    transparency_requirements: List[str] = field(default_factory=list)


class DigitalRightsGovernance:
    def __init__(self) -> None:
        self.rights_registry: dict[str, RightsProfile] = {}
        self.policies: dict[str, GovernancePolicy] = {}

    def register_entity(self, entity_id: str, rights: List[RightType]) -> RightsProfile:
        profile = RightsProfile(
            entity_id=entity_id,
            rights=rights,
            consent_records=[],
        )
        self.rights_registry[entity_id] = profile
        return profile

    def enforce_policy(self, entity_id: str, policy_id: str) -> bool:
        profile = self.rights_registry.get(entity_id)
        policy = self.policies.get(policy_id)
        if not profile or not policy:
            return False
        return self._check_compliance(profile, policy)

    def _check_compliance(self, profile: RightsProfile, policy: GovernancePolicy) -> bool:
        required_rights = {RightType.AUTONOMY, RightType.DIGNITY, RightType.NON_DISCRIMINATION}
        return required_rights.issubset(set(profile.rights))

    def add_policy(self, policy: GovernancePolicy) -> None:
        self.policies[policy.policy_id] = policy

    def resolve_conflict(self, entity_id: str, right_a: RightType, right_b: RightType) -> RightType:
        priority = [RightType.DIGNITY, RightType.AUTONOMY, RightType.PRIVACY, RightType.NON_DISCRIMINATION]
        candidates = [r for r in priority if r in {right_a, right_b}]
        return candidates[0] if candidates else right_a
