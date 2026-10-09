from typing import Any, Dict, List, Optional, Tuple


class DeductiveReasoner:
    def __init__(self):
        self._premises: List[str] = []
        self._rules: List[Dict[str, Any]] = []

    def add_premise(self, premise: str) -> None:
        self._premises.append(premise)

    def add_rule(self, rule_id: str, antecedent: List[str], consequent: str) -> None:
        self._rules.append({
            "id": rule_id,
            "antecedent": antecedent,
            "consequent": consequent,
        })

    def apply_modus_ponens(self, antecedent: str, implication: Tuple[str, str]) -> Optional[str]:
        rule_id, consequent = implication
        if antecedent == rule_id:
            return consequent
        return None

    def derive(self, goal: str) -> Optional[str]:
        for rule in self._rules:
            if rule["consequent"] == goal and all(a in self._premises for a in rule["antecedent"]):
                return rule["consequent"]
        return None
