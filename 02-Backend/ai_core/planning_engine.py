from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import heapq


@dataclass
class State:
    id: str
    data: Dict[str, Any]
    is_terminal: bool = False
    g_cost: float = 0.0
    h_cost: float = 0.0

    @property
    def f_cost(self) -> float:
        return self.g_cost + self.h_cost


@dataclass
class Action:
    name: str
    preconditions: Dict[str, Any]
    effects: Dict[str, Any]
    cost: float = 1.0


class StateSpacePlanner:
    def __init__(self, heuristic_weight: float = 1.0):
        self.heuristic_weight = heuristic_weight
        self._plan_log: List[Dict[str, Any]] = []

    def plan(self, start: State, goal: State, actions: List[Action]) -> List[Action]:
        open_set = [(start.f_cost, 0, start)]
        came_from: Dict[str, Tuple[Optional[State], Optional[Action]]] = {}
        g_score: Dict[str, float] = {start.id: 0.0}
        visited = set()
        counter = 0

        while open_set:
            _, _, current = heapq.heappop(open_set)
            if current.id in visited:
                continue
            visited.add(current.id)

            if self._satisfies(current.data, goal.data):
                return self._reconstruct_plan(came_from, current)

            for action in self._applicable_actions(current, actions):
                neighbor_data = dict(current.data)
                neighbor_data.update(action.effects)
                neighbor = State(
                    id=f"{current.id}->{action.name}",
                    data=neighbor_data,
                    g_cost=current.g_cost + action.cost,
                    h_cost=self._heuristic(neighbor_data, goal.data),
                )
                tentative_g = current.g_cost + action.cost
                if neighbor.id in g_score and tentative_g >= g_score[neighbor.id]:
                    continue
                g_score[neighbor.id] = tentative_g
                came_from[neighbor.id] = (current, action)
                counter += 1
                heapq.heappush(open_set, (neighbor.f_cost, counter, neighbor))
        return []

    def _applicable_actions(self, state: State, actions: List[Action]) -> List[Action]:
        applicable = []
        for action in actions:
            if all(state.data.get(k) == v for k, v in action.preconditions.items()):
                applicable.append(action)
        return applicable

    def _heuristic(self, state_data: Dict[str, Any], goal_data: Dict[str, Any]) -> float:
        missing = sum(1 for k, v in goal_data.items() if state_data.get(k) != v)
        return float(missing) * self.heuristic_weight

    def _satisfies(self, state_data: Dict[str, Any], goal_data: Dict[str, Any]) -> bool:
        return all(state_data.get(k) == v for k, v in goal_data.items())

    def _reconstruct_plan(self, came_from: Dict[str, Tuple[Optional[State], Optional[Action]]],
                          end_state: State) -> List[Action]:
        plan = []
        current = end_state
        while current.id in came_from and came_from[current.id][1] is not None:
            _, action = came_from[current.id]
            plan.append(action)
            current, _ = came_from[current.id]
        plan.reverse()
        return plan


class HierarchicalGoalNetwork:
    def __init__(self):
        self.goals: Dict[str, Dict[str, Any]] = {}
        self.dependencies: Dict[str, List[str]] = {}
        self._status: Dict[str, str] = {}

    def add_goal(self, goal_id: str, description: str, priority: float = 1.0) -> None:
        self.goals[goal_id] = {"description": description, "priority": priority}
        self._status[goal_id] = "pending"

    def add_dependency(self, goal_id: str, prerequisite: str) -> None:
        if goal_id not in self.dependencies:
            self.dependencies[goal_id] = []
        self.dependencies[goal_id].append(prerequisite)

    def topo_order(self) -> List[str]:
        in_degree = {g: 0 for g in self.goals}
        for g, deps in self.dependencies.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[g] += 1
        queue = [g for g, d in in_degree.items() if d == 0]
        result = []
        while queue:
            node = queue.pop(0)
            result.append(node)
            for g, deps in self.dependencies.items():
                if node in deps:
                    in_degree[g] -= 1
                    if in_degree[g] == 0:
                        queue.append(g)
        return result

    def get_execution_sequence(self) -> List[str]:
        order = self.topo_order()
        order.sort(key=lambda g: self.goals[g]["priority"], reverse=True)
        return order


class PlanningEngine:
    def __init__(self):
        self.planner = StateSpacePlanner()
        self.goal_network = HierarchicalGoalNetwork()
        self._plan_history: List[Dict[str, Any]] = []

    def define_goal(self, goal_id: str, description: str, priority: float = 1.0) -> None:
        self.goal_network.add_goal(goal_id, description, priority=priority)

    def add_dependency(self, goal_id: str, prerequisite: str) -> None:
        self.goal_network.add_dependency(goal_id, prerequisite)

    def plan_actions(self, start_state: State, goal_state: State, actions: List[Action]) -> List[Action]:
        plan = self.planner.plan(start_state, goal_state, actions)
        entry = {
            "start": start_state.id,
            "goal": goal_state.id,
            "plan_length": len(plan),
            "total_cost": sum(a.cost for a in plan),
        }
        self._plan_history.append(entry)
        return plan

    def get_goal_sequence(self) -> List[str]:
        return self.goal_network.get_execution_sequence()

    def get_plan_history(self) -> List[Dict[str, Any]]:
        return list(self._plan_history)
