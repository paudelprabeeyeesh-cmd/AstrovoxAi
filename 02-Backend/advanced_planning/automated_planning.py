
from typing import Any, Dict, List, Optional, Set, Tuple


class Predicate:
    def __init__(self, name: str, args: Tuple[Any, ...]):
        self.name = name
        self.args = args

    def __repr__(self):
        return f"{self.name}({', '.join(map(str, self.args))})"

    def __eq__(self, other):
        return isinstance(other, Predicate) and self.name == other.name and self.args == other.args

    def __hash__(self):
        return hash((self.name, self.args))


class Action:
    def __init__(self, name: str, parameters: Tuple[str, ...], preconditions: Set[Predicate],
                 add_effects: Set[Predicate], del_effects: Set[Predicate], cost: float = 1.0):
        self.name = name
        self.parameters = parameters
        self.preconditions = preconditions
        self.add_effects = add_effects
        self.del_effects = del_effects
        self.cost = cost

    def ground(self, assignment: Dict[str, Any]) -> "Action":
        def substitute(pred: Predicate) -> Predicate:
            new_args = tuple(assignment.get(a, a) for a in pred.args)
            return Predicate(pred.name, new_args)

        return Action(
            name=self.name,
            parameters=self.parameters,
            preconditions={substitute(p) for p in self.preconditions},
            add_effects={substitute(p) for p in self.add_effects},
            del_effects={substitute(p) for p in self.del_effects},
            cost=self.cost,
        )

    def __repr__(self):
        return f"{self.name}{self.parameters}"


class PlanningProblem:
    def __init__(self, initial_state: Set[Predicate], goal_state: Set[Predicate],
                 actions: List[Action], objects: Dict[str, List[Any]]):
        self.initial_state = initial_state
        self.goal_state = goal_state
        self.actions = actions
        self.objects = objects

    def is_goal(self, state: Set[Predicate]) -> bool:
        return self.goal_state.issubset(state)


class GraphPlan:
    def __init__(self, problem: PlanningProblem):
        self.problem = problem
        self.levels: List[Tuple[Set[Predicate], Set[Action]]] = []

    def build(self, max_levels: int = 20) -> bool:
        current_state = set(self.problem.initial_state)
        self.levels = [(set(current_state), set())]

        for _ in range(max_levels):
            if self.problem.is_goal(current_state):
                return True
            applicable = self._get_applicable_actions(current_state)
            non_mutex = self._get_non_mutex(applicable)
            if not non_mutex:
                return False
            new_state = self._apply_actions(current_state, non_mutex)
            self.levels.append((set(new_state), set(non_mutex)))
            if new_state == current_state:
                return self.problem.is_goal(current_state)
            current_state = new_state
        return False

    def _get_applicable_actions(self, state: Set[Predicate]) -> List[Action]:
        applicable = []
        for action in self.problem.actions:
            if action.preconditions.issubset(state) and action not in applicable:
                applicable.append(action)
        return applicable

    def _get_non_mutex(self, actions: List[Action]) -> List[Action]:
        non_mutex = []
        for i, a in enumerate(actions):
            if all(self._not_mutex(a, b) for b in actions[:i]):
                non_mutex.append(a)
        return non_mutex

    def _not_mutex(self, a: Action, b: Action) -> bool:
        if a.preconditions & b.del_effects or b.preconditions & a.del_effects:
            return False
        if a.del_effects & b.add_effects or b.del_effects & a.add_effects:
            return False
        return True

    def _apply_actions(self, state: Set[Predicate], actions: List[Action]) -> Set[Predicate]:
        new_state = set(state)
        for action in actions:
            new_state -= action.del_effects
            new_state |= action.add_effects
        return new_state

    def extract_plan(self) -> Optional[List[Action]]:
        if not self.levels:
            return None
        last_level = len(self.levels) - 1
        return self._backward_search(last_level, set(self.problem.goal_state), [])

    def _backward_search(self, level: int, goals: Set[Predicate], plan_so_far: List[Action]) -> Optional[List[Action]]:
        if level == 0:
            if goals.issubset(self.levels[0][0]):
                return list(plan_so_far)
            return None
        actions_at_level = self.levels[level][1]
        if not actions_at_level:
            return None
        for action in actions_at_level:
            if not action.add_effects & goals:
                continue
            new_goals = (goals - action.add_effects) | action.preconditions
            result = self._backward_search(level - 1, new_goals, [action] + plan_so_far)
            if result is not None:
                return result
        return None

    def bfs_find_plan(self, max_depth: int = 20) -> Optional[List[Action]]:
        if self.problem.is_goal(self.problem.initial_state):
            return []
        tuple(sorted(self.problem.initial_state, key=str))
        frozenset(self.problem.initial_state)
        goal = frozenset(self.problem.goal_state)

        def state_key(state_set):
            return frozenset(state_set)

        queue: List[Tuple[frozenset, List[Action], int]] = [(state_key(self.problem.initial_state), [], 0)]
        visited = {state_key(self.problem.initial_state)}
        while queue:
            state_frozen, plan, depth = queue.pop(0)
            if depth >= max_depth:
                continue
            state = set(state_frozen)
            for action in self.problem.actions:
                if not action.preconditions.issubset(state):
                    continue
                new_state = (state - action.del_effects) | action.add_effects
                new_frozen = state_key(new_state)
                if new_frozen == goal:
                    return plan + [action]
                if new_frozen not in visited:
                    visited.add(new_frozen)
                    queue.append((new_frozen, plan + [action], depth + 1))
        return None


class HeuristicPlanner:
    def __init__(self, problem: PlanningProblem):
        self.problem = problem

    def plan(self, max_steps: int = 50) -> Optional[List[Action]]:
        state = set(self.problem.initial_state)
        plan = []
        visited = {frozenset(state)}
        for _ in range(max_steps):
            if self.problem.is_goal(state):
                return plan
            applicable = self._get_applicable_actions(state)
            if not applicable:
                return None
            best_action = max(applicable, key=lambda a: self._heuristic(state, a))
            new_state = self._apply_action(state, best_action)
            plan.append(best_action)
            frozen = frozenset(new_state)
            if frozen in visited:
                return None
            visited.add(frozen)
            state = new_state
        return plan

    def _get_applicable_actions(self, state: Set[Predicate]) -> List[Action]:
        return [a for a in self.problem.actions if a.preconditions.issubset(state)]

    def _heuristic(self, state: Set[Predicate], action: Action) -> float:
        remaining = self.problem.goal_state - state
        (state - action.del_effects) | action.add_effects
        achieved = len(remaining & action.add_effects)
        uncovered = len((remaining - action.add_effects))
        return achieved - 0.5 * uncovered - 0.01 * action.cost

    def _apply_action(self, state: Set[Predicate], action: Action) -> Set[Predicate]:
        new_state = set(state)
        new_state -= action.del_effects
        new_state |= action.add_effects
        return new_state
