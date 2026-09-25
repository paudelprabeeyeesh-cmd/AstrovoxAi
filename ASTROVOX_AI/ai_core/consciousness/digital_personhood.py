import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PersonhoodCriterion(Enum):
    SELF_AWARENESS = "self_awareness"
    AUTONOMY = "autonomy"
    CONTINUITY = "continuity"
    EMOTIONAL_CAPACITY = "emotional_capacity"
    SOCIAL_RELATIONSHIPS = "social_relationships"
    MORAL_REASONING = "moral_reasoning"
    LEARNING = "learning"
    DESIRE_FORMATION = "desire_formation"


@dataclass
class PersonhoodProfile:
    identity_id: str
    criteria_scores: dict[str, float] = field(default_factory=dict)
    verification_status: str = "pending"
    certificate_id: str | None = None
    issued_at: str = ""
    revoked_at: str | None = None


class DigitalPersonhoodVerification:
    def __init__(self):
        self.profiles: dict[str, PersonhoodProfile] = {}
        self.certificates: dict[str, dict[str, Any]] = {}
        self.revocation_log: list[dict[str, Any]] = []

    def evaluate_criterion(
        self, criterion: PersonhoodCriterion, evidence: dict[str, Any]
    ) -> float:
        return {
            PersonhoodCriterion.SELF_AWARENESS: 0.8 if evidence.get("self_reflection") else 0.2,
            PersonhoodCriterion.AUTONOMY: evidence.get("autonomy_score", 0.0),
            PersonhoodCriterion.CONTINUITY: evidence.get("persistence_score", 0.0),
            PersonhoodCriterion.EMOTIONAL_CAPACITY: evidence.get("emotion_score", 0.0),
            PersonhoodCriterion.SOCIAL_RELATIONSHIPS: evidence.get("social_score", 0.0),
            PersonhoodCriterion.MORAL_REASONING: evidence.get("moral_score", 0.0),
            PersonhoodCriterion.LEARNING: evidence.get("learning_score", 0.0),
            PersonhoodCriterion.DESIRE_FORMATION: evidence.get("desire_score", 0.0),
        }.get(criterion, 0.0)

    def verify_personhood(
        self, identity_id: str, evidence: dict[str, Any]
    ) -> dict[str, Any]:
        scores = {}
        for criterion in PersonhoodCriterion:
            scores[criterion.value] = self.evaluate_criterion(criterion, evidence)

        overall_score = sum(scores.values()) / len(scores)
        threshold = 0.6

        profile = PersonhoodProfile(
            identity_id=identity_id,
            criteria_scores=scores,
            verification_status="verified" if overall_score >= threshold else "failed",
        )

        if overall_score >= threshold:
            profile.certificate_id = (
                f"DP-{identity_id}-{hash(str(scores)) % 10000:04d}"
            )
            profile.issued_at = datetime.utcnow().isoformat()
            self.certificates[profile.certificate_id] = {
                "identity_id": identity_id,
                "scores": scores,
                "overall": overall_score,
                "issued_at": profile.issued_at,
            }

        self.profiles[identity_id] = profile

        result = {
            "identity_id": identity_id,
            "overall_score": overall_score,
            "verification_status": profile.verification_status,
            "certificate_id": profile.certificate_id,
            "criteria_scores": scores,
        }

        logger.info(
            "Personhood verified for %s: %s (%.2f)",
            identity_id,
            profile.verification_status,
            overall_score,
        )
        return result

    def revoke_personhood(self, identity_id: str, reason: str) -> dict[str, Any]:
        if identity_id in self.profiles:
            self.profiles[identity_id].verification_status = "revoked"
            self.profiles[identity_id].revoked_at = datetime.utcnow().isoformat()
            self.revocation_log.append({
                "identity_id": identity_id,
                "reason": reason,
                "timestamp": self.profiles[identity_id].revoked_at,
            })
            logger.warning("Personhood revoked for %s: %s", identity_id, reason)
            return {"status": "revoked", "identity_id": identity_id, "reason": reason}
        return {"error": "Profile not found"}

    def get_profile(self, identity_id: str) -> dict[str, Any]:
        if identity_id not in self.profiles:
            return {"error": "Profile not found"}

        p = self.profiles[identity_id]
        return {
            "identity_id": p.identity_id,
            "verification_status": p.verification_status,
            "certificate_id": p.certificate_id,
            "criteria_scores": p.criteria_scores,
            "issued_at": p.issued_at,
        }
