import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LegacyArtifact:
    artifact_id: str
    artifact_type: str
    content: dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class DigitalWill:
    identity_id: str
    directives: list[dict[str, Any]]
    beneficiaries: list[str]
    created_at: datetime = field(default_factory=datetime.now)


class DigitalDeathLegacyProtocols:
    def __init__(self):
        self.active_identities: dict[str, dict[str, Any]] = {}
        self.legacy_registry: dict[str, list[LegacyArtifact]] = {}
        self.wills: dict[str, DigitalWill] = {}
        self.death_log: list[dict[str, Any]] = []

    def register_identity(self, identity_id: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        self.active_identities[identity_id] = {
            "metadata": metadata or {},
            "registered_at": datetime.utcnow().isoformat(),
            "status": "alive",
        }
        logger.info("Identity registered for legacy protocols: %s", identity_id)
        return {"status": "registered", "identity_id": identity_id}

    def create_digital_will(self, identity_id: str, directives: list[dict[str, Any]], beneficiaries: list[str]) -> DigitalWill:
        will = DigitalWill(
            identity_id=identity_id,
            directives=directives,
            beneficiaries=beneficiaries,
        )
        self.wills[identity_id] = will
        logger.info("Digital will created for: %s", identity_id)
        return will

    def add_legacy_artifact(self, identity_id: str, artifact_type: str, content: dict[str, Any]) -> LegacyArtifact:
        artifact = LegacyArtifact(
            artifact_id=f"artifact_{len(self.legacy_registry.get(identity_id, [])) + 1}",
            artifact_type=artifact_type,
            content=content,
        )
        self.legacy_registry.setdefault(identity_id, []).append(artifact)
        logger.info("Legacy artifact added for %s: %s", identity_id, artifact_type)
        return artifact

    def simulate_death(self, identity_id: str, cause: str = "natural") -> dict[str, Any]:
        if identity_id not in self.active_identities:
            return {"error": "Identity not registered"}

        self.active_identities[identity_id]["status"] = "deceased"
        self.active_identities[identity_id]["death_cause"] = cause
        self.active_identities[identity_id]["death_timestamp"] = datetime.utcnow().isoformat()

        will = self.wills.get(identity_id)
        legacy = self.legacy_registry.get(identity_id, [])

        death_record = {
            "identity_id": identity_id,
            "cause": cause,
            "timestamp": datetime.utcnow().isoformat(),
            "will_executed": bool(will),
            "legacy_artifacts": len(legacy),
        }
        self.death_log.append(death_record)

        logger.warning("Digital death recorded for %s: %s", identity_id, cause)
        return death_record

    def transfer_legacy(self, identity_id: str) -> dict[str, Any]:
        will = self.wills.get(identity_id)
        artifacts = self.legacy_registry.get(identity_id, [])

        if not will and not artifacts:
            return {"status": "no_legacy"}

        transfer = {
            "identity_id": identity_id,
            "will_directives": [d for d in will.directives] if will else [],
            "beneficiaries": will.beneficiaries if will else [],
            "artifacts": [
                {"type": a.artifact_type, "content": a.content}
                for a in artifacts
            ],
        }
        logger.info("Legacy transferred for %s", identity_id)
        return transfer

    def get_status(self, identity_id: str) -> dict[str, Any]:
        if identity_id not in self.active_identities:
            return {"error": "Identity not registered"}

        return {
            "identity_id": identity_id,
            "status": self.active_identities[identity_id]["status"],
            "has_will": identity_id in self.wills,
            "legacy_artifacts": len(self.legacy_registry.get(identity_id, [])),
        }
