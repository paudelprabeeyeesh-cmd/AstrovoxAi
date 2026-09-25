"""Affiliate system."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta


@dataclass
class Affiliate:
    affiliate_id: str
    user_id: str
    code: str
    commission_rate: float
    total_earnings: float = 0.0
    clicks: int = 0
    conversions: int = 0
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AffiliateSystem:
    _affiliates: Dict[str, Affiliate] = {}
    _codes: Dict[str, Affiliate] = {}

    @classmethod
    def register(cls, user_id: str, code: str, commission_rate: float = 0.10) -> Affiliate:
        affiliate_id = f"aff_{user_id}"
        affiliate = Affiliate(
            affiliate_id=affiliate_id,
            user_id=user_id,
            code=code,
            commission_rate=commission_rate,
        )
        cls._affiliates[affiliate_id] = affiliate
        cls._codes[code] = affiliate
        return affiliate

    @classmethod
    def track_click(cls, code: str) -> bool:
        affiliate = cls._codes.get(code)
        if affiliate:
            affiliate.clicks += 1
            return True
        return False

    @classmethod
    def record_conversion(cls, code: str, amount: float) -> Optional[float]:
        affiliate = cls._codes.get(code)
        if affiliate:
            affiliate.conversions += 1
            commission = amount * affiliate.commission_rate
            affiliate.total_earnings += commission
            return commission
        return None
