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


class DigitalDeathProtocols:
    def __init__(self):
        self.deaths: list[DigitalDeathProtocol] = []
        self.active: bool = True

    def initiate_death(self, entity_id: str, reason: str = "natural_end") -> DigitalDeathProtocol:
        protocol = DigitalDeathProtocol(
            entity_id=entity_id,
            reason=reason,
            data_preserved=False,
            legacy_activated=False,
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
