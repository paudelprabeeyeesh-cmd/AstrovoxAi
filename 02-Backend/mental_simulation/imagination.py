from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Scenario:
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    plausibility: float = 0.5


class ImaginationEngine:
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        self.scenarios: List[Scenario] = []

    def generate(self, action: str, context: Dict[str, Any], n: int = 3) -> List[Scenario]:
        generated: List[Scenario] = []
        for i in range(n):
            plausibility = 0.3 + (0.4 * ((i + 1) / max(n, 1)))
            desc = f"{action} in {context.get('setting', 'unknown')} variant {i + 1}"
            generated.append(Scenario(description=desc, context=context, plausibility=plausibility))
        self.scenarios.extend(generated)
        return generated

    def evaluate(self, scenario: Scenario) -> float:
        return max(0.0, min(1.0, scenario.plausibility))
