import numpy as np
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Outcome:
    description: str
    utility: float
    probability: float
    risk: float = 0.0


class UtilityFunction:
    def __init__(self, risk_aversion: float = 1.0):
        self.risk_aversion = risk_aversion

    def evaluate(self, outcomes: List[Outcome]) -> float:
        expected = sum(o.probability * o.utility for o in outcomes)
        variance = float(np.var([o.utility for o in outcomes])) if len(outcomes) > 1 else 0.0
        penalty = self.risk_aversion * variance
        return expected - penalty

    def expected_value(self, outcomes: List[Outcome]) -> float:
        return sum(o.probability * o.utility for o in outcomes)

    def certainty_equivalent(self, outcomes: List[Outcome]) -> float:
        return self.evaluate(outcomes)


class DecisionTree:
    def __init__(self):
        self.tree: Dict[str, Any] = {}

    def add_decision(self, node_id: str, options: List[str], outcomes: Dict[str, List[Outcome]]) -> None:
        self.tree[node_id] = {"type": "decision", "options": options, "outcomes": outcomes}

    def evaluate(self, root_id: str, utility_fn: UtilityFunction) -> Dict[str, float]:
        scores = {}
        node = self.tree.get(root_id)
        if not node:
            return scores
        for opt in node["options"]:
            outcomes = node["outcomes"].get(opt, [])
            scores[opt] = utility_fn.evaluate(outcomes)
        return scores

    def optimal_choice(self, root_id: str, utility_fn: UtilityFunction) -> Optional[str]:
        scores = self.evaluate(root_id, utility_fn)
        if not scores:
            return None
        return max(scores, key=scores.get)


class MarkovDecisionProcess:
    def __init__(self, n_states: int, n_actions: int, discount: float = 0.95):
        self.n_states = n_states
        self.n_actions = n_actions
        self.discount = discount
        self.transitions = np.zeros((n_states, n_actions, n_states))
        self.rewards = np.zeros((n_states, n_actions, n_states))
        self.value_function = np.zeros(n_states)
        self.policy = np.zeros(n_states, dtype=int)

    def set_transition(self, s: int, a: int, s_prime: int, prob: float) -> None:
        self.transitions[s, a, s_prime] = prob

    def set_reward(self, s: int, a: int, s_prime: int, reward: float) -> None:
        self.rewards[s, a, s_prime] = reward

    def value_iteration(self, tol: float = 1e-6, max_iter: int = 1000) -> np.ndarray:
        for _ in range(max_iter):
            new_values = np.zeros(self.n_states)
            for s in range(self.n_states):
                q_values = np.zeros(self.n_actions)
                for a in range(self.n_actions):
                    expected = np.sum(
                        self.transitions[s, a] * (self.rewards[s, a] + self.discount * self.value_function)
                    )
                    q_values[a] = expected
                new_values[s] = np.max(q_values)
                self.policy[s] = int(np.argmax(q_values))
            if np.max(np.abs(new_values - self.value_function)) < tol:
                break
            self.value_function = new_values
        return self.value_function

    def policy_evaluation(self) -> np.ndarray:
        return self.value_function


class DecisionMaker:
    def __init__(self, risk_aversion: float = 1.0):
        self.utility_fn = UtilityFunction(risk_aversion=risk_aversion)
        self.decision_tree = DecisionTree()
        self._decision_log: List[Dict[str, Any]] = []

    def choose(self, decision_id: str, options: List[str],
               outcomes: Dict[str, List[Outcome]]) -> Optional[str]:
        self.decision_tree.add_decision(decision_id, options, outcomes)
        choice = self.decision_tree.optimal_choice(decision_id, self.utility_fn)
        entry = {
            "decision_id": decision_id,
            "choice": choice,
            "scores": self.decision_tree.evaluate(decision_id, self.utility_fn),
        }
        self._decision_log.append(entry)
        return choice

    def solve_mdp(self, mdp: MarkovDecisionProcess) -> np.ndarray:
        return mdp.value_iteration()

    def get_decision_log(self) -> List[Dict[str, Any]]:
        return list(self._decision_log)
