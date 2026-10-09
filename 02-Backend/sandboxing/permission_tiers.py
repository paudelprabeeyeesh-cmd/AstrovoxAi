import enum
from dataclasses import dataclass


class PermissionTier(enum.Enum):
    READ = "read"
    WRITE = "write"
    DANGEROUS = "dangerous"


@dataclass
class PermissionDecision:
    tier: PermissionTier
    approved: bool
    reversible: bool
    message: str = ""


class PermissionEngine:
    DANGEROUS_KEYWORDS = {"rm -rf", "drop table", "delete from", "truncate", "format"}

    def evaluate(self, operation: str, tier: PermissionTier) -> PermissionDecision:
        lowered = operation.lower()
        if tier == PermissionTier.READ:
            return PermissionDecision(
                tier=PermissionTier.READ,
                approved=True,
                reversible=True,
                message="auto-approved read",
            )
        if tier == PermissionTier.WRITE:
            return PermissionDecision(
                tier=PermissionTier.WRITE,
                approved=False,
                reversible=True,
                message="write requires confirmation",
            )
        if tier == PermissionTier.DANGEROUS:
            dangerous = any(k in lowered for k in self.DANGEROUS_KEYWORDS)
            return PermissionDecision(
                tier=PermissionTier.DANGEROUS,
                approved=not dangerous,
                reversible=not dangerous,
                message="dangerous operation denied" if dangerous else "dangerous tier requires review",
            )
        return PermissionDecision(
            tier=tier,
            approved=False,
            reversible=False,
            message="unknown tier",
        )

    def confirm(self, operation: str, tier: PermissionTier) -> PermissionDecision:
        decision = self.evaluate(operation, tier)
        if tier == PermissionTier.WRITE and not decision.approved:
            decision.approved = True
            decision.message = "write confirmed by user"
        return decision

    def reverse(self, operation: str, tier: PermissionTier) -> bool:
        decision = self.evaluate(operation, tier)
        return decision.reversible
