
import random
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class Plan:
    def __init__(self, actions: List[Any]):
        self.actions = list(actions)
        self.valid = True
        self.failure_reason: Optional[str] = None

    def __len__(self) -> int:
        return len(self.actions)

    def __getitem__(self, idx):
        return self.actions[idx]

    def __repr__(self):
        return f"Plan({self.actions})"


class PlanRepairEngine:
    def __init__(self, is_valid_fn: Callable[[Plan], bool], apply_fn: Callable[[Any, Any], Any],
                 get_actions_fn: Callable[[Any], List[Any]]):
        self.is_valid_fn = is_valid_fn
        self.apply_fn = apply_fn
        self.get_actions_fn = get_actions_fn
        self.repair_history: List[Dict[str, Any]] = []

    def diagnose(self, plan: Plan, initial_state: Any) -> Optional[int]:
        state = initial_state
        for i, action in enumerate(plan.actions):
            valid_actions = self.get_actions_fn(state)
            if action not in valid_actions:
                return i
            state = self.apply_fn(state, action)
        return None

    def repair_remove(self, plan: Plan, initial_state: Any) -> Plan:
        failure_idx = self.diagnose(plan, initial_state)
        if failure_idx is None:
            return plan
        repaired = Plan(plan.actions[:failure_idx] + plan.actions[failure_idx + 1:])
        repaired.valid = self.is_valid_fn(repaired)
        self.repair_history.append({
            "type": "remove",
            "failed_index": failure_idx,
            "success": repaired.valid,
        })
        return repaired

    def repair_substitute(self, plan: Plan, initial_state: Any, alternatives: Dict[int, List[Any]]) -> Optional[Plan]:
        failure_idx = self.diagnose(plan, initial_state)
        if failure_idx is None or failure_idx not in alternatives:
            return None
        for alt_action in alternatives[failure_idx]:
            new_plan = Plan(plan.actions[:failure_idx] + [alt_action] + plan.actions[failure_idx + 1:])
            if self.is_valid_fn(new_plan):
                new_plan.valid = True
                self.repair_history.append({"type": "substitute", "failed_index": failure_idx, "alt_action": alt_action,
                                            "success": True})
                return new_plan
        return None

    def repair_insert(self, plan: Plan, initial_state: Any) -> Plan:
        failure_idx = self.diagnose(plan, initial_state)
        if failure_idx is None:
            return plan
        state_at_failure = initial_state
        for i in range(failure_idx):
            state_at_failure = self.apply_fn(state_at_failure, plan.actions[i])
        possible = [a for a in self.get_actions_fn(state_at_failure) if a != plan.actions[failure_idx]]
        if not possible:
            return self.repair_remove(plan, initial_state)
        best = max(possible, key=lambda a: self._action_score(state_at_failure, a))
        repaired = Plan(plan.actions[:failure_idx] + [best, plan.actions[failure_idx]] + plan.actions[failure_idx + 1:])
        repaired.valid = self.is_valid_fn(repaired)
        self.repair_history.append({"type": "insert", "failed_index": failure_idx, "inserted_action": best,
                                    "success": repaired.valid})
        return repaired

    def _action_score(self, state: Any, action: Any) -> float:
        return random.random()


class Replanner:
    def __init__(self, is_goal_fn: Callable[[Any], bool], get_actions_fn: Callable[[Any], List[Any]],
                 apply_fn: Callable[[Any, Any], Any], heuristic_fn: Callable[[Any, Any], float]):
        self.is_goal_fn = is_goal_fn
        self.get_actions_fn = get_actions_fn
        self.apply_fn = apply_fn
        self.heuristic_fn = heuristic_fn
        self.replan_count = 0

    def replan(self, current_state: Any, failed_plan: Plan, max_actions: int = 20) -> Optional[Plan]:
        self.replan_count += 1
        plan = self._astar_search(current_state, max_actions)
        if plan is not None:
            plan.valid = True
        return plan

    def _astar_search(self, start: Any, max_actions: int) -> Optional[Plan]:
        str(hash(str(start)))
        frontier: List[Tuple[float, int, Any, List[Any]]] = [(0.0, 0, start, [])]
        visited: Set[str] = set()
        counter = 0
        while frontier:
            _, depth, state, actions = frontier.pop(0)
            state_id = str(hash(str(state)))
            if self.is_goal_fn(state):
                return Plan(actions)
            if depth >= max_actions:
                continue
            if state_id in visited:
                continue
            visited.add(state_id)
            for action in self.get_actions_fn(state):
                try:
                    new_state = self.apply_fn(state, action)
                except Exception as _e:  # noqa: BLE001
                    continue
                g = len(actions) + 1
                h = self.heuristic_fn(new_state)
                priority = g + h
                counter += 1
                frontier.append((priority, counter, new_state, actions + [action]))
            frontier.sort(key=lambda x: x[0])
        return None
