"""Coupon engine for discounts and promotions."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import secrets


class DiscountType(Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    FREE_TRIAL = "free_trial"


class CouponStatus(Enum):
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class Coupon:
    coupon_id: str
    code: str
    discount_type: DiscountType
    discount_value: float
    currency: str = "usd"
    min_amount: float = 0.0
    max_uses: int = 1
    current_uses: int = 0
    status: CouponStatus = CouponStatus.ACTIVE
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CouponEngine:
    _coupons: Dict[str, Coupon] = {}
    _codes: Dict[str, Coupon] = {}

    @classmethod
    def create_coupon(cls, discount_type: DiscountType, discount_value: float, expires_days: int = 30, max_uses: int = 1) -> Coupon:
        code = secrets.token_urlsafe(16).upper()
        coupon_id = f"coupon_{code.lower()}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
        coupon = Coupon(
            coupon_id=coupon_id,
            code=code,
            discount_type=discount_type,
            discount_value=discount_value,
            max_uses=max_uses,
            expires_at=expires_at,
        )
        cls._coupons[coupon_id] = coupon
        cls._codes[code] = coupon
        return coupon

    @classmethod
    def validate(cls, code: str, amount: float) -> Optional[Coupon]:
        coupon = cls._codes.get(code.upper())
        if not coupon or coupon.status != CouponStatus.ACTIVE:
            return None
        if coupon.expires_at and coupon.expires_at < datetime.now(timezone.utc):
            coupon.status = CouponStatus.EXPIRED
            return None
        if coupon.current_uses >= coupon.max_uses:
            return None
        if amount < coupon.min_amount:
            return None
        return coupon

    @classmethod
    def apply(cls, code: str, amount: float) -> tuple[Optional[Coupon], float]:
        coupon = cls.validate(code, amount)
        if not coupon:
            return None, amount
        if coupon.discount_type == DiscountType.PERCENTAGE:
            discount = amount * (coupon.discount_value / 100)
        else:
            discount = min(coupon.discount_value, amount)
        coupon.current_uses += 1
        if coupon.current_uses >= coupon.max_uses:
            coupon.status = CouponStatus.USED
        return coupon, amount - discount
