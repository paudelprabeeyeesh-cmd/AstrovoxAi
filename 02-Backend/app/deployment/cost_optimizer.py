from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from ..deployment.base_adapter import BaseCloudAdapter


@dataclass
class CostEstimate:
    service: str
    monthly_cost: float
    unit: str = "USD"
    currency: str = "USD"
    confidence: float = 0.9
    breakdown: Optional[Dict[str, float]] = None


@dataclass
class OptimizationRecommendation:
    service: str
    current_cost: float
    recommended_cost: float
    savings: float
    action: str
    priority: str


class CostOptimizer:
    def __init__(self, adapter: BaseCloudAdapter):
        self.adapter = adapter
        self.estimates: List[CostEstimate] = []
        self.recommendations: List[OptimizationRecommendation] = []

    def estimate_monthly_cost(self, service: str, usage: Dict[str, Any]) -> CostEstimate:
        pricing = self._get_pricing(service, usage)
        estimate = CostEstimate(
            service=service,
            monthly_cost=pricing,
            breakdown=usage,
        )
        self.estimates.append(estimate)
        return estimate

    def _get_pricing(self, service: str, usage: Dict[str, Any]) -> float:
        base_prices = {
            "s3_storage": 0.023,
            "ecr_storage": 0.10,
            "eks_cluster": 73.0,
            "gpu_instance": 3.06,
            "data_transfer": 0.09,
            "cloudfront": 0.085,
        }
        price = base_prices.get(service, 1.0)
        quantity = usage.get("quantity", 1)
        return price * quantity

    def generate_recommendations(self) -> List[OptimizationRecommendation]:
        recommendations = []
        for estimate in self.estimates:
            if estimate.monthly_cost > 100:
                recommendations.append(
                    OptimizationRecommendation(
                        service=estimate.service,
                        current_cost=estimate.monthly_cost,
                        recommended_cost=estimate.monthly_cost * 0.7,
                        savings=estimate.monthly_cost * 0.3,
                        action="Enable auto-scaling and use spot instances",
                        priority="high",
                    )
                )
        self.recommendations = recommendations
        return recommendations

    def get_cost_report(self) -> Dict[str, Any]:
        total_cost = sum(e.monthly_cost for e in self.estimates)
        total_savings = sum(r.savings for r in self.recommendations)
        return {
            "total_monthly_cost": total_cost,
            "total_potential_savings": total_savings,
            "service_estimates": [
                {
                    "service": e.service,
                    "monthly_cost": e.monthly_cost,
                    "unit": e.unit,
                }
                for e in self.estimates
            ],
            "recommendations": [
                {
                    "service": r.service,
                    "action": r.action,
                    "savings": r.savings,
                    "priority": r.priority,
                }
                for r in self.recommendations
            ],
        }
