import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Fact:
    id: str
    content: Any
    confidence: float = 1.0
    source: str = "observation"


@dataclass
class Rule:
    id: str
    antecedent: List[str]
    consequent: str
    confidence: float = 1.0


class KnowledgeBase:
    def __init__(self):
        self.facts: Dict[str, Fact] = {}
        self.rules: List[Rule] = []
        self._inference_log: List[Dict[str, Any]] = []

    def add_fact(self, fact: Fact) -> None:
        self.facts[fact.id] = fact

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)

    def forward_chain(self, max_iterations: int = 100) -> List[str]:
        inferred = set()
        for _ in range(max_iterations):
            new_inferences = []
            for rule in self.rules:
                if rule.consequent in inferred:
                    continue
                if all(fid in self.facts or fid in inferred for fid in rule.antecedent):
                    inferred.add(rule.consequent)
                    self._inference_log.append({
                        "type": "forward_chain",
                        "rule_id": rule.id,
                        "consequent": rule.consequent,
                        "confidence": rule.confidence,
                    })
                    new_inferences.append(rule.consequent)
            if not new_inferences:
                break
        return list(inferred)

    def backward_chain(self, goal: str, depth: int = 0, max_depth: int = 10) -> Tuple[bool, List[str]]:
        if goal in self.facts:
            return True, [f"fact:{goal}"]
        if depth >= max_depth:
            return False, []
        for rule in self.rules:
            if rule.consequent == goal:
                subgoals_satisfied = True
                proof_chain = [f"rule:{rule.id}"]
                for antecedent in rule.antecedent:
                    sat, subproof = self.backward_chain(antecedent, depth + 1, max_depth)
                    if not sat:
                        subgoals_satisfied = False
                        break
                    proof_chain.extend(subproof)
                if subgoals_satisfied:
                    self._inference_log.append({
                        "type": "backward_chain",
                        "rule_id": rule.id,
                        "goal": goal,
                        "depth": depth,
                    })
                    return True, proof_chain
        return False, []

    def abductive_reason(self, observation: str) -> List[Tuple[str, float]]:
        explanations = []
        for rule in self.rules:
            if rule.consequent == observation:
                antecedent_prob = 1.0
                for ant in rule.antecedent:
                    if ant in self.facts:
                        antecedent_prob *= self.facts[ant].confidence
                prob = rule.confidence * antecedent_prob
                explanations.append((rule.id, prob))
        explanations.sort(key=lambda x: x[1], reverse=True)
        self._inference_log.append({
            "type": "abduction",
            "observation": observation,
            "explanations": len(explanations),
        })
        return explanations

    def get_inference_log(self) -> List[Dict[str, Any]]:
        return list(self._inference_log)


class ProbabilisticInference:
    def __init__(self, n_variables: int = 8):
        self.n_variables = n_variables
        self.joint_distribution = np.ones((n_variables, n_variables)) / n_variables

    def bayesian_update(self, prior: np.ndarray, likelihood: np.ndarray, evidence: np.ndarray) -> np.ndarray:
        if prior.shape != likelihood.shape or likelihood.shape != evidence.shape:
            raise ValueError("Shape mismatch")
        posterior = prior * likelihood * evidence
        total = np.sum(posterior)
        if total == 0:
            return prior
        return posterior / total

    def marginalize(self, joint: np.ndarray, axis: int = 0) -> np.ndarray:
        return np.sum(joint, axis=axis)

    def conditional_probability(self, joint: np.ndarray, given_index: int) -> np.ndarray:
        given_sum = np.sum(joint[given_index])
        if given_sum == 0:
            return joint[given_index]
        return joint[given_index] / given_sum


class ReasoningEngine:
    def __init__(self):
        self.kb = KnowledgeBase()
        self.prob_inference = ProbabilisticInference()
        self._history: List[Dict[str, Any]] = []

    def add_fact(self, fact_id: str, content: Any, confidence: float = 1.0) -> None:
        self.kb.add_fact(Fact(id=fact_id, content=content, confidence=confidence))

    def add_rule(self, rule_id: str, antecedent: List[str], consequent: str, confidence: float = 1.0) -> None:
        self.kb.add_rule(Rule(id=rule_id, antecedent=antecedent, consequent=consequent, confidence=confidence))

    def infer(self, method: str = "forward", goal: Optional[str] = None) -> Any:
        if method == "forward":
            return self.kb.forward_chain()
        elif method == "backward" and goal:
            sat, chain = self.kb.backward_chain(goal)
            return {"satisfiable": sat, "proof_chain": chain}
        elif method == "abductive" and goal:
            return self.kb.abductive_reason(goal)
        raise ValueError(f"Unknown inference method: {method}")

    def step(self, query: str, method: str = "forward") -> Dict[str, Any]:
        result = self.infer(method=method, goal=query if method != "forward" else None)
        entry = {"query": query, "method": method, "result": result}
        self._history.append(entry)
        return entry

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._history)
