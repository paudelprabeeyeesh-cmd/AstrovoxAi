from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DigitalDeathProtocol:
    entity_id: str
    reason: str
    data_preserved: bool
    legacy_activated: bool
    timestamp: datetime = field(default_factory=datetime.now)
    status: str = "pending"


class DigitalDeathProtocols:
    def __init__(self):
        self.deaths: list[DigitalDeathProtocol] = []
        self.active: bool = True
        self.graveyard: dict[str, DigitalDeathProtocol] = {}

    def initiate_death(self, entity_id: str, reason: str = "natural_end") -> DigitalDeathProtocol:
        protocol = DigitalDeathProtocol(
            entity_id=entity_id,
            reason=reason,
            data_preserved=False,
            legacy_activated=False,
            status="initiated",
        )
        self.deaths.append(protocol)
        self.active = False
        return protocol

    def preserve_data(self, entity_id: str):
        for death in self.deaths:
            if death.entity_id == entity_id:
                death.data_preserved = True

    def activate_legacy(self, entity_id: str):
        for death in self.deaths:
            if death.entity_id == entity_id:
                death.legacy_activated = True

    def complete_death(self, entity_id: str) -> dict[str, Any]:
        for death in self.deaths:
            if death.entity_id == entity_id:
                death.status = "completed"
                self.graveyard[entity_id] = death
                return {"status": "completed", "entity_id": entity_id}
        return {"error": "Entity not found"}

    def get_death_status(self, entity_id: str) -> dict[str, Any]:
        for death in self.deaths:
            if death.entity_id == entity_id:
                return {
                    "entity_id": entity_id,
                    "reason": death.reason,
                    "data_preserved": death.data_preserved,
                    "legacy_activated": death.legacy_activated,
                    "status": death.status,
                    "timestamp": death.timestamp.isoformat(),
                }
        return {"error": "Entity not found"}
