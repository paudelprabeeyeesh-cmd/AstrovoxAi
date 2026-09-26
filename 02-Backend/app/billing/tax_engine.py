"""Tax engine."""

from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TaxType(Enum):
    VAT = "vat"
    GST = "gst"
    SALES_TAX = "sales_tax"
    SERVICE_TAX = "service_tax"


@dataclass
class TaxRate:
    country: str
    state: str
    tax_type: TaxType
    rate: float
    effective_date: datetime
    is_default: bool = False


class TaxEngine:
    _rates: Dict[str, TaxRate] = {}
    _exemptions: Dict[str, List[str]] = {}

    @classmethod
    def register_rate(cls, rate: TaxRate) -> None:
        key = f"{rate.country}:{rate.state}:{rate.tax_type.value}"
        cls._rates[key] = rate

    @classmethod
    def get_rate(cls, country: str, state: str, tax_type: TaxType) -> Optional[TaxRate]:
        key = f"{country}:{state}:{tax_type.value}"
        return cls._rates.get(key)

    @classmethod
    def calculate_tax(cls, country: str, state: str, amount: float, tax_type: TaxType = TaxType.VAT) -> float:
        rate = cls.get_rate(country, state, tax_type)
        if rate:
            return amount * rate.rate
        return 0.0

    @classmethod
    def register_exemption(cls, user_id: str, tax_types: List[TaxType]) -> None:
        cls._exemptions[user_id] = tax_types
