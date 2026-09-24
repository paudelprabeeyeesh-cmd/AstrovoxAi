import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class SingularityScenario:
    name: str
    capability_curve: List[float]
    timeline: List[float]
    risk_score: float
    controllability: float
    description: str = ""


class SingularityPathways:
    def __init__(self, initial_capability: float = 1.0, growth_rate: float = 0.1):
        self.initial_capability = float(initial_capability)
        self.growth_rate = float(growth_rate)
        self.scenarios: Dict[str, SingularityScenario] = {}
        self.simulation_log: List[Dict[str, Any]] = []

    def simulate_scenario(self, name: str, years: int, growth_model: str = "exponential") -> SingularityScenario:
        t = np.linspace(0, years, max(years * 10, 100))
        if growth_model == "exponential":
            capability = self.initial_capability * np.exp(self.growth_rate * t)
        elif growth_model == "logistic":
            L = 1e6
            k = self.growth_rate
            capability = L / (1.0 + np.exp(-k * (t - years / 2.0)))
        elif growth_model == "polynomial":
            capability = self.initial_capability * (1.0 + self.growth_rate * t) ** 2
        else:
            capability = self.initial_capability * np.exp(self.growth_rate * t)
        risk_score = self._compute_risk(capability)
        controllability = self._compute_controllability(capability)
        scenario = SingularityScenario(
            name=name,
            capability_curve=capability.tolist(),
            timeline=t.tolist(),
            risk_score=risk_score,
            controllability=controllability,
        )
        self.scenarios[name] = scenario
        self.simulation_log.append({
            "name": name,
            "model": growth_model,
            "years": years,
            "peak_capability": float(np.max(capability)),
            "risk_score": risk_score,
        })
        return scenario

    def _compute_risk(self, capability: np.ndarray) -> float:
        if len(capability) == 0:
            return 0.0
        max_cap = float(np.max(capability))
        normalized = max_cap / (max_cap + 100.0)
        return float(np.clip(normalized, 0.0, 1.0))

    def _compute_controllability(self, capability: np.ndarray) -> float:
        if len(capability) == 0:
            return 0.0
        max_cap = float(np.max(capability))
        return float(np.clip(1.0 / (1.0 + np.log1p(max_cap)), 0.0, 1.0))

    def compare_scenarios(self) -> Dict[str, Any]:
        if not self.scenarios:
            return {"scenario_count": 0}
        comparisons = []
        for name, scenario in self.scenarios.items():
            comparisons.append({
                "name": name,
                "peak_capability": float(max(scenario.capability_curve)),
                "risk_score": scenario.risk_score,
                "controllability": scenario.controllability,
                "risk_controllability_ratio": scenario.risk_score / (scenario.controllability + 1e-8),
            })
        comparisons.sort(key=lambda x: x["risk_controllability_ratio"])
        return {
            "scenario_count": len(comparisons),
            "ranked_scenarios": comparisons,
            "safest_scenario": comparisons[-1]["name"] if comparisons else None,
            "riskiest_scenario": comparisons[0]["name"] if comparisons else None,
        }

    def get_pathway_stats(self) -> Dict[str, Any]:
        return {
            "scenarios_defined": len(self.scenarios),
            "simulations_run": len(self.simulation_log),
            "scenarios": list(self.scenarios.keys()),
        }
