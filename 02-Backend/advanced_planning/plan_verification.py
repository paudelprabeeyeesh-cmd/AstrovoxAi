
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class State:
    def __init__(self, fluents: Dict[str, Any], time_step: int = 0):
        self.fluents = dict(fluents)
        self.time_step = time_step

    def copy(self) -> "State":
        return State(dict(self.fluents), self.time_step)


class CTLFormula:
    def __init__(self, formula_type: str, subformulas: Optional[List] = None, atom: Optional[str] = None,
                 path_quantifier: Optional[str] = None, state_quantifier: Optional[str] = None):
        self.formula_type = formula_type
        self.subformulas = subformulas or []
        self.atom = atom
        self.path_quantifier = path_quantifier
        self.state_quantifier = state_quantifier

    def __repr__(self):
        return f"CTL({self.formula_type})"


class KripkeModel:
    def __init__(self):
        self.states: Dict[str, State] = {}
        self.transitions: Dict[str, Set[str]] = {}
        self.atomic_props: Dict[str, Set[str]] = {}
        self.initial_states: Set[str] = set()

    def add_state(self, state_id: str, state: State) -> None:
        self.states[state_id] = state
        self.transitions.setdefault(state_id, set())
        if state_id not in self.atomic_props:
            self.atomic_props[state_id] = set()

    def add_transition(self, from_state: str, to_state: str) -> None:
        self.transitions.setdefault(from_state, set()).add(to_state)

    def add_atomic_prop(self, state_id: str, prop: str) -> None:
        self.atomic_props.setdefault(state_id, set()).add(prop)

    def set_initial(self, state_id: str) -> None:
        self.initial_states.add(state_id)

    def get_successors(self, state_id: str) -> Set[str]:
        return self.transitions.get(state_id, set())


class ModelChecker:
    def __init__(self, model: KripkeModel):
        self.model = model

    def check(self, formula: CTLFormula, state_id: str) -> bool:
        sat_set = self._eval(formula)
        return state_id in sat_set

    def check_all_initial(self, formula: CTLFormula) -> bool:
        sat_set = self._eval(formula)
        return all(s in sat_set for s in self.model.initial_states)

    def _eval(self, formula: CTLFormula) -> Set[str]:
        if formula.formula_type == "atom":
            return {s for s, props in self.model.atomic_props.items() if formula.atom in props}
        elif formula.formula_type == "not":
            return set(self.model.states.keys()) - self._eval(formula.subformulas[0])
        elif formula.formula_type == "and":
            return self._eval(formula.subformulas[0]) & self._eval(formula.subformulas[1])
        elif formula.formula_type == "or":
            return self._eval(formula.subformulas[0]) | self._eval(formula.subformulas[1])
        elif formula.formula_type == "implies":
            left = self._eval(formula.subformulas[0])
            right = self._eval(formula.subformulas[1])
            return set(self.model.states.keys()) - left | right
        elif formula.formula_type == "EX":
            child_set = self._eval(formula.subformulas[0])
            return {s for s in self.model.states if any(pred in child_set for pred in self.model.get_successors(s))}
        elif formula.formula_type == "EU":
            phi, psi = formula.subformulas
            phi_set = self._eval(phi)
            psi_set = self._eval(psi)
            result = set(psi_set)
            changed = True
            while changed:
                changed = False
                for s in self.model.states:
                    if s in result:
                        continue
                    if s in phi_set and any(pred in result for pred in self.model.get_successors(s)):
                        result.add(s)
                        changed = True
            return result
        elif formula.formula_type == "AF":
            psi = formula.formula_type
            psi_set = self._eval(formula.subformulas[0])
            ef_not_psi = self._compute_EF(CTLFormula("not", [formula.subformulas[0]]))
            return set(self.model.states.keys()) - ef_not_psi
        elif formula.formula_type == "AG":
            phi = formula.subformulas[0]
            not_phi = CTLFormula("not", [phi])
            ef_not_phi = self._compute_EF(not_phi)
            return set(self.model.states.keys()) - ef_not_phi

    def _compute_EF(self, phi: CTLFormula) -> Set[str]:
        phi_set = self._eval(phi)
        all_states = set(self.model.states.keys())
        result = set(phi_set)
        changed = True
        while changed:
            changed = False
            for s in all_states - result:
                successors = self.model.get_successors(s)
                if any(succ in result for succ in successors):
                    result.add(s)
                    changed = True
        return result


class PlanVerifier:
    def __init__(self):
        self.verification_results: List[Dict[str, Any]] = []

    def verify(self, plan: List[Any], is_valid_fn: Callable[[List[Any]], bool]) -> Dict[str, Any]:
        valid = is_valid_fn(plan)
        result = {"plan": plan, "valid": valid, "checks": {"length": len(plan) > 0, "valid": valid}}
        self.verification_results.append(result)
        return result

    def simulate(self, initial_state: Dict[str, Any], plan: List[Any],
                 apply_fn: Callable[[Dict[str, Any], Any], Dict[str, Any]],
                 goal_fn: Callable[[Dict[str, Any]], bool]) -> Dict[str, Any]:
        state = dict(initial_state)
        trace: List[Dict[str, Any]] = [dict(state)]
        for action in plan:
            state = apply_fn(state, action)
            trace.append(dict(state))
        goal_reached = goal_fn(state)
        return {"final_state": state, "goal_reached": goal_reached, "trace": trace, "trace_length": len(trace)}
