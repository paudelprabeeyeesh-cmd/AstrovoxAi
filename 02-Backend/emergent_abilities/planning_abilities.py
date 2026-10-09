import numpy as np
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class PlanningResult:
    plan: List[str]
    horizon: int
    success: bool
    expected_reward: float
    actual_reward: float


class PlanningAbilityModel:
    def __init__(self, state_dim: int, action_dim: int, horizon: int = 10):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.horizon = horizon
        self.W_state = np.random.randn(state_dim, state_dim) * 0.02
        self.W_action = np.random.randn(state_dim, action_dim) * 0.02
        self.W_value = np.random.randn(state_dim, 1) * 0.02

    def transition(self, state: np.ndarray, action: np.ndarray) -> np.ndarray:
        return np.tanh(state @ self.W_state + action @ self.W_action.T)

    def value_estimate(self, state: np.ndarray) -> float:
        return float(np.squeeze(state @ self.W_value))

    def plan(self, initial_state: np.ndarray, goal_state: np.ndarray, num_actions: int = 5) -> PlanningResult:
        current_state = initial_state.copy()
        plan = []
        total_expected_reward = 0.0
        for step in range(self.horizon):
            best_action, best_value = None, -float('inf')
            for a in range(num_actions):
                action_vec = np.zeros(self.action_dim)
                action_vec[a % self.action_dim] = 1.0
                next_state = self.transition(current_state, action_vec)
                value = self.value_estimate(next_state) - 0.1 * np.linalg.norm(next_state - goal_state)
                if value > best_value:
                    best_value = value
                    best_action = a
            if best_action is None:
                break
            plan.append(f"action_{best_action}")
            current_state = self.transition(current_state, np.eye(self.action_dim)[best_action % self.action_dim])
            total_expected_reward += best_value
        dist_to_goal = np.linalg.norm(current_state - goal_state)
        success = dist_to_goal < 0.5
        return PlanningResult(plan=plan, horizon=self.horizon, success=success,
                              expected_reward=float(total_expected_reward), actual_reward=float(-dist_to_goal))

    def compute_planning_horizon(self, model_sizes: np.ndarray, task_difficulties: np.ndarray) -> np.ndarray:
        horizons = []
        for size in model_sizes:
            horizon_capability = min(self.horizon, int(np.log2(size)) % self.horizon + 1)
            achievable = [t for t in task_difficulties if t <= horizon_capability / self.horizon]
            horizons.append(len(achievable) / max(len(task_difficulties), 1))
        return np.array(horizons)


class PlanningEmergenceAnalyzer:
    def __init__(self):
        self.planning_results: List[PlanningResult] = []
        self.horizon_success_rates: Dict[int, List[bool]] = {}

    def record_plan(self, result: PlanningResult):
        self.planning_results.append(result)
        h = result.horizon
        if h not in self.horizon_success_rates:
            self.horizon_success_rates[h] = []
        self.horizon_success_rates[h].append(result.success)

    def success_rate_by_horizon(self) -> np.ndarray:
        if not self.horizon_success_rates:
            return np.array([])
        return np.array([np.mean(v) for v in self.horizon_success_rates.values()])

    def horizon_emergence_threshold(self) -> float:
        if not self.planning_results:
            return 0.0
        success_rates = np.array([1.0 if r.success else 0.0 for r in self.planning_results])
        if len(success_rates) < 3:
            return float(len(success_rates))
        for i in range(1, len(success_rates)):
            if success_rates[i] > success_rates[i - 1] + 0.2:
                return float(i + 1)
        return float(len(success_rates))
