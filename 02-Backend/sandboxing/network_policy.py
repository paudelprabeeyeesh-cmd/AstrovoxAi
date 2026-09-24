import re
from dataclasses import dataclass, field
from typing import FrozenSet, List


@dataclass(frozen=True)
class NetworkPolicy:
    default_deny: bool = True
    allowlist_domains: FrozenSet[str] = field(default_factory=frozenset)
    credential_isolation: bool = True

    def check_egress(self, target: str) -> bool:
        if not self.default_deny:
            return True
        normalized = target.lower().strip()
        for domain in self.allowlist_domains:
            if normalized == domain.lower() or normalized.endswith("." + domain.lower()):
                return True
        return False

    def isolate_credentials(self, operation: str) -> str:
        if not self.credential_isolation:
            return operation
        pattern = re.compile(r"(password|token|secret|api[_-]?key)\s*=\s*\S+", re.IGNORECASE)
        return pattern.sub("[REDACTED]", operation)
