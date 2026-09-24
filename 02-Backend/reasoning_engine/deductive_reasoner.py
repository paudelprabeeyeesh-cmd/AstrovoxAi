from typing import Any, Dict, List, Optional, Tuple


class DeductiveReasoner:
    def __init__(self):
        self._premises: List[str] = []
        self._conclusions: List[str] = []

    def add_premise(self, premise: str) -> None:
        self._premises.append(premise)

    def add_rule(self, rule_id: str, antecedent: List[str], consequent: str) -> None:
        self._conclusions.append(f"{rule_id}:{consequent}")

    def apply_modus_ponens(self, antecedent: str, implication: Tuple[str, str]) -> Optional[str]:
        rule_id, consequent = implication
        if antecedent == rule_id:
            return consequent
        return None

    def derive(self, goal: str) -> Optional[str]:
        for premise in self._premises:
            for conclusion in self._conclusions:
                rule_id, consequent = conclusion.split(":", 1)
                if premise == rule_id and consequent == goal:
                    return consequent
        return None
