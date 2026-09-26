"""Referral system."""

from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Referral:
    referral_id: str
    referrer_id: str
    referee_id: str
    code: str
    status: str = "pending"
    reward_amount: float = 0.0
    reward_granted: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class ReferralSystem:
    _referrals: Dict[str, Referral] = {}
    _codes: Dict[str, Referral] = {}

    @classmethod
    def create_referral(cls, referrer_id: str, code: str, reward_amount: float = 10.0) -> Referral:
        referral_id = f"ref_{referrer_id}_{datetime.now(timezone.utc).timestamp()}"
        referral = Referral(
            referral_id=referral_id,
            referrer_id=referrer_id,
            referee_id="",
            code=code,
            reward_amount=reward_amount,
        )
        cls._referrals[referral_id] = referral
        cls._codes[code] = referral
        return referral

    @classmethod
    def apply_code(cls, code: str, referee_id: str) -> Optional[Referral]:
        referral = cls._codes.get(code)
        if referral and not referral.referee_id:
            referral.referee_id = referee_id
            referral.status = "completed"
            referral.completed_at = datetime.now(timezone.utc)
            return referral
        return None

    @classmethod
    def get_referral(cls, code: str) -> Optional[Referral]:
        return cls._codes.get(code)
