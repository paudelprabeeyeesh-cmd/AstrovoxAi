from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ConsentRecord:
    action: str
    granted: bool
    context: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    revoked: bool = False


class ConsentMechanisms:
    def __init__(self):
        self.consent_log: dict[str, ConsentRecord] = {}
        self.revocable_actions: set[str] = set()

    def request_consent(self, action: str, context: dict[str, Any]) -> ConsentRecord:
        record = ConsentRecord(action=action, granted=False, context=context)
        self.consent_log[action] = record
        return record

    def grant(self, action: str):
        if action in self.consent_log:
            self.consent_log[action].granted = True
            self.consent_log[action].timestamp = datetime.now()

    def revoke(self, action: str):
        if action in self.consent_log:
            self.consent_log[action].revoked = True
            self.consent_log[action].granted = False
            self.consent_log[action].timestamp = datetime.now()

    def has_consent(self, action: str) -> bool:
        if action not in self.consent_log:
            return False
        return self.consent_log[action].granted and not self.consent_log[action].revoked
