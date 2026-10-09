from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class World:
    facts: Dict[str, str]
    name: str = "base"


@dataclass
class Counterfactual:
    id: str
    antecedent: str
    consequent: str
    base_world: World
    alternative_world: World
    confidence: float = 0.5


class CounterfactualReasoner:
    def __init__(self):
        self.worlds: Dict[str, World] = {"base": World(facts={}, name="base")}
        self.counterfactuals: Dict[str, Counterfactual] = {}

    def add_world(self, world: World) -> None:
        self.worlds[world.name] = world

    def generate(self, antecedent: str, consequent: str, base_name: str = "base") -> Counterfactual:
        base = self.worlds.get(base_name)
        if base is None:
            raise KeyError(f"World {base_name} not found")
        alt_facts = dict(base.facts)
        alt_facts[antecedent] = "assumed"
        cid = f"cf-{len(self.counterfactuals) + 1}"
        cf = Counterfactual(
            id=cid,
            antecedent=antecedent,
            consequent=consequent,
            base_world=base,
            alternative_world=World(facts=alt_facts, name=f"alt-{cid}"),
            confidence=0.5,
        )
        self.counterfactuals[cid] = cf
        return cf

    def evaluate(self, cf_id: str) -> Dict[str, float]:
        cf = self.counterfactuals[cf_id]
        score = 0.7 if cf.antecedent in cf.alternative_world.facts else 0.3
        return {"consistency": score, "confidence": cf.confidence}
