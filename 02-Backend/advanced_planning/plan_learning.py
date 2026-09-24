
import numpy as np
from typing import Any, Callable, Dict, List, Optional, Tuple


class Demonstrator:
    def __init__(self):
        self.demonstrations: List[Dict[str, Any]] = []

    def record(self, initial_state: Any, action_sequence: List[Any], outcome: Any,
               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        demo = {
            "initial_state": initial_state,
            "actions": list(action_sequence),
            "outcome": outcome,
            "context": context or {},
            "length": len(action_sequence),
        }
        self.demonstrations.append(demo)
        return demo

    def get_demonstrations(self) -> List[Dict[str, Any]]:
        return list(self.demonstrations)


class PlanLearner:
    def __init__(self):
        self.learned_plans: List[Dict[str, Any]] = []
        self.skill_library: Dict[str, List[Any]] = {}

    def learn_from_demonstrations(self, demonstrations: List[Dict[str, Any]],
                                  state_encoder: Optional[Callable[[Any], np.ndarray]] = None) -> Dict[str, Any]:
        if not demonstrations:
            return {"error": "no demonstrations"}
        state_encoder = state_encoder or self._default_encoder
        encoded_states = [state_encoder(d["initial_state"]) for d in demonstrations]
        action_sequences = [d["actions"] for d in demonstrations]
        outcomes = [d["outcome"] for d in demonstrations]
        max_len = max(len(seq) for seq in action_sequences)
        plan_matrix = np.zeros((len(action_sequences), max_len), dtype=int)
        for i, seq in enumerate(action_sequences):
            plan_matrix[i, :len(seq)] = [hash(str(a)) % 100000 for a in seq]
        mean_plan = np.mean(plan_matrix, axis=0).astype(int)
        learned_plan = self._decode_plan(mean_plan, demonstrations, plan_matrix)
        skill_signature = str(mean_plan[:3])
        self.skill_library.setdefault(skill_signature, []).append(learned_plan)
        result = {
            "plan": learned_plan,
            "num_demonstrations": len(demonstrations),
            "avg_length": float(np.mean([len(seq) for seq in action_sequences])),
            "success_rate": float(np.mean(outcomes)),
            "skill_signature": skill_signature,
        }
        self.learned_plans.append(result)
        return result

    def _default_encoder(self, state: Any) -> np.ndarray:
        if isinstance(state, dict):
            vals = []
            for k, v in sorted(state.items()):
                if isinstance(v, (int, float)):
                    vals.append(float(v))
                else:
                    vals.append(float(hash(str(v)) % 10000))
            return np.array(vals + [0.0] * (10 - len(vals)))
        return np.zeros(10)

    def _decode_plan(self, mean_plan: np.ndarray, demonstrations: List[Dict], plan_matrix: np.ndarray) -> List[Any]:
        actions_map: Dict[int, List[Any]] = {}
        for i, demo in enumerate(demonstrations):
            for j, action in enumerate(demo["actions"]):
                code = plan_matrix[i, j]
                actions_map.setdefault(code, []).append(action)
        decoded = []
        for code in mean_plan:
            if code in actions_map:
                decoded.append(actions_map[code][0])
            else:
                decoded.append(None)
        return decoded

    def generalize(self, new_state: Any, state_encoder: Optional[Callable[[Any], np.ndarray]] = None) -> Optional[List[Any]]:
        if not self.learned_plans:
            return None
        state_encoder = state_encoder or self._default_encoder
        new_encoded = state_encoder(new_state)
        best_plan = self.learned_plans[0]["plan"]
        best_sim = -1.0
        for learned in self.learned_plans:
            plan = learned["plan"]
            if len(plan) == 0:
                continue
            sim = self._similarity(new_encoded, plan)
            if sim > best_sim:
                best_sim = sim
                best_plan = plan
        return best_plan if best_sim > 0 else None

    def _similarity(self, state: np.ndarray, plan: List[Any]) -> float:
        plan_codes = np.array([hash(str(a)) % 100000 for a in plan if a is not None])
        if len(plan_codes) == 0:
            return 0.0
        combined = np.concatenate([state.flatten(), plan_codes])
        return float(np.mean(np.abs(combined)))
