import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class IdentitySnapshot:
    identity_hash: str
    state: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)


class IdentityPersistence:
    def __init__(self):
        self.snapshots: list[IdentitySnapshot] = []
        self.current_identity_hash: str | None = None

    def snapshot(self, state: dict[str, Any]) -> IdentitySnapshot:
        state_str = str(sorted(state.items()))
        identity_hash = hashlib.sha256(state_str.encode()).hexdigest()
        snapshot = IdentitySnapshot(
            identity_hash=identity_hash,
            state=state,
        )
        self.snapshots.append(snapshot)
        self.current_identity_hash = identity_hash
        return snapshot

    def verify_identity(self, state: dict[str, Any]) -> bool:
        state_str = str(sorted(state.items()))
        identity_hash = hashlib.sha256(state_str.encode()).hexdigest()
        if not self.current_identity_hash:
            return False
        return identity_hash == self.current_identity_hash
