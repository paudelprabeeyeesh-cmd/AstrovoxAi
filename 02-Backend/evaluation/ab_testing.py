import math
import logging
from typing import Any
from dataclasses import dataclass, field
from statistics import mean, variance

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VariantConfig:
    name: str
    weight: float = 0.5
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "weight": self.weight, "metadata": self.metadata}


@dataclass
class VariantResult:
    variant_name: str
    impressions: int
    conversions: int
    values: list[float] = field(default_factory=list)

    def conversion_rate(self) -> float:
        return self.conversions / self.impressions if self.impressions > 0 else 0.0

    def mean_value(self) -> float:
        return float(np.mean(self.values)) if self.values else 0.0

    def std_value(self) -> float:
        return float(np.std(self.values)) if self.values else 0.0


class ABTest:
    def __init__(self, name: str, variants: list[VariantConfig]):
        self.name = name
        self._variants = {v.name: v for v in variants}
        self._results: dict[str, VariantResult] = {v.name: VariantResult(variant_name=v.name, impressions=0, conversions=0) for v in variants}
        self._start_time = None
        self._end_time = None
        self._minimum_sample_size = 100

    def get_variant(self, name: str) -> VariantConfig | None:
        return self._variants.get(name)

    def get_result(self, name: str) -> VariantResult | None:
        return self._results.get(name)

    def record_impression(self, variant_name: str) -> None:
        result = self._results.get(variant_name)
        if result:
            result.impressions += 1

    def record_conversion(self, variant_name: str, value: float = 1.0) -> None:
        result = self._results.get(variant_name)
        if result:
            result.conversions += 1
            result.values.append(value)

    def get_variant(self, name: str) -> VariantConfig | None:
        return self._variants.get(name)

    def run(self, hours: float = 24.0) -> dict[str, Any]:
        import time
        self._start_time = time.time()
        return self.results()

    def results(self) -> dict[str, Any]:
        variant_summaries = {}
        for name, result in self._results.items():
            variant_summaries[name] = {
                "impressions": result.impressions,
                "conversions": result.conversions,
                "conversion_rate": round(result.conversion_rate(), 4),
                "mean_value": round(result.mean_value(), 4),
            }
        comparison = self._compare_variants()
        return {
            "test_name": self.name,
            "variants": variant_summaries,
            "comparison": comparison,
        }

    def _compare_variants(self) -> dict[str, Any]:
        names = list(self._results.keys())
        if len(names) < 2:
            return {"winner": None, "p_value": None, "significant": False}
        a_name, b_name = names[0], names[1]
        a = self._results[a_name]
        b = self._results[b_name]
        p_value = self._two_proportion_ztest(a.conversions, a.impressions, b.conversions, b.impressions)
        return {
            "control": a_name,
            "treatment": b_name,
            "control_rate": round(a.conversion_rate(), 4),
            "treatment_rate": round(b.conversion_rate(), 4),
            "relative_lift": round((b.conversion_rate() - a.conversion_rate()) / a.conversion_rate() if a.conversion_rate() > 0 else 0.0, 4),
            "p_value": round(p_value, 6),
            "significant": p_value < 0.05,
            "winner": b_name if (p_value < 0.05 and b.conversion_rate() > a.conversion_rate()) else a_name,
        }

    def _two_proportion_ztest(self, x1: int, n1: int, x2: int, n2: int) -> float:
        p1 = x1 / n1 if n1 > 0 else 0.0
        p2 = x2 / n2 if n2 > 0 else 0.0
        p_pool = (x1 + x2) / (n1 + n2) if (n1 + n2) > 0 else 0.0
        if p_pool == 0 or p_pool == 1:
            return 1.0
        se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
        if se == 0:
            return 1.0
        z = (p1 - p2) / se
        return 2 * (1 - self._normal_cdf(abs(z)))

    def _normal_cdf(self, x: float) -> float:
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def t_test(self, variant_a: str, variant_b: str) -> dict[str, Any]:
        a = self._results.get(variant_a)
        b = self._results.get(variant_b)
        if not a or not b or len(a.values) < 2 or len(b.values) < 2:
            return {"t_statistic": None, "p_value": None, "significant": False}
        t_stat, p_value = self._welch_t_test(a.values, b.values)
        return {
            "t_statistic": round(t_stat, 4),
            "p_value": round(p_value, 6),
            "significant": p_value < 0.05,
        }

    def _welch_t_test(self, group_a: list[float], group_b: list[float]) -> tuple[float, float]:
        a = np.array(group_a)
        b = np.array(group_b)
        n1, n2 = len(a), len(b)
        m1, m2 = float(np.mean(a)), float(np.mean(b))
        v1, v2 = float(np.var(a, ddof=1)), float(np.var(b, ddof=1))
        se = math.sqrt(v1 / n1 + v2 / n2)
        if se == 0:
            return 0.0, 1.0
        t = (m1 - m2) / se
        df = (v1 / n1 + v2 / n2) ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1))
        p = 2 * (1 - self._normal_cdf(abs(t)))
        return t, p

    def add_sample_data(self, variant_name: str, values: list[float]) -> None:
        result = self._results.get(variant_name)
        if result:
            result.values.extend(values)
            result.impressions += len(values)

    def minimum_sample_size(self, baseline_rate: float, mde: float, alpha: float = 0.05, power: float = 0.8) -> int:
        z_alpha = 1.96
        z_beta = 0.84
        p1 = baseline_rate
        p2 = baseline_rate + mde
        p_avg = (p1 + p2) / 2
        numerator = (z_alpha * math.sqrt(2 * p_avg * (1 - p_avg)) + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
        denominator = (p1 - p2) ** 2
        return math.ceil(numerator / denominator) if denominator > 0 else 0
