from typing import List, Dict, Optional, Set


class KripkeModel:
    def __init__(self, worlds: Optional[List[str]] = None, accessibility: Optional[Dict[str, Set[str]]] = None):
        self.worlds = worlds or ["w0", "w1"]
        self.valuation: Dict[str, Dict[str, bool]] = {"w0": {}, "w1": {}}
        self.accessibility = accessibility or {"w0": {"w1"}, "w1": {"w0"}}
        self.current_world: str = "w0"

    def add_world(self, world: str):
        if world not in self.worlds:
            self.worlds.append(world)
            self.valuation[world] = {}

    def add_atomic(self, world: str, symbol: str, value: bool):
        if world not in self.valuation:
            self.valuation[world] = {}
        self.valuation[world][symbol] = value

    def set_accessibility(self, source: str, targets: Set[str]):
        self.accessibility[source] = targets

    def possible_worlds(self, world: str) -> Set[str]:
        return self.accessibility.get(world, set())

    def truth(self, symbol: str, world: str) -> bool:
        return self.valuation.get(world, {}).get(symbol, False)

    def effective_valuation(self, world: str) -> Dict[str, bool]:
        return self.valuation.get(world, {})

    def counter(self, world: str, symbols: Optional[List[str]] = None) -> Dict[str, int]:
        vals = self.valuation.get(world, {})
        if symbols:
            vals = {s: vals.get(s, False) for s in symbols}
        true_count = sum(1 for v in vals.values() if v)
        return {"true": true_count, "false": len(vals) - true_count, "total": len(vals)}

    def structure_mapping(self, source: str, target: str) -> float:
        v_s = self.valuation.get(source, {})
        v_t = self.valuation.get(target, {})
        if not v_s or not v_t:
            return 0.0
        common = set(v_s.keys()) & set(v_t.keys())
        if not common:
            return 0.0
        matches = sum(1 for k in common if v_s[k] == v_t[k])
        return matches / len(common)


class ModalFormula:
    def __init__(self, operator: str, proposition: str, modal_depth: int = 0):
        self.operator = operator
        self.proposition = proposition
        self.modal_depth = modal_depth

    def box(self, prop: str) -> "ModalFormula":
        return ModalFormula("box", prop, self.modal_depth + 1)

    def diamond(self, prop: str) -> "ModalFormula":
        return ModalFormula("diamond", prop, self.modal_depth + 1)

    def truth_in_model(self, model: KripkeModel, world: str) -> bool:
        if self.operator == "box":
            return all(model.truth(self.proposition, w) for w in model.possible_worlds(world))
        elif self.operator == "diamond":
            return any(model.truth(self.proposition, w) for w in model.possible_worlds(world))
        else:
            return model.truth(self.proposition, world)

    def necessary(self, model: KripkeModel, world: str) -> bool:
        return self.truth_in_model(model, world)

    def possible(self, model: KripkeModel, world: str) -> bool:
        return self.truth_in_model(model, world)


class ModalEngine:
    def __init__(self):
        self.model = KripkeModel()
        self.external_knowledge: Dict[str, Dict[str, bool]] = {}

    def add_world(self, world: str):
        self.model.add_world(world)

    def add_knowledge(self, world: str, symbol: str, value: bool):
        self.model.add_atomic(world, symbol, value)

    def is_necessary(self, symbol: str, world: str) -> bool:
        return ModalFormula("box", symbol).truth_in_model(self.model, world)

    def is_possible(self, symbol: str, world: str) -> bool:
        return ModalFormula("diamond", symbol).truth_in_model(self.model, world)

    def effective_truth(self, symbol: str, world: str) -> bool:
        return self.model.truth(symbol, world)
