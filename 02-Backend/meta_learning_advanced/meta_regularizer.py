from typing import Dict, List, Optional

from dataclasses import dataclass


@dataclass
class RegularizationConfig:
    l2_lambda: float = 1e-4
    weight_decay_lambda: float = 0.0
    consistency_lambda: float = 0.0
    prior_params: Optional[Dict[str, float]] = None


class MetaRegularizer:
    def __init__(self, config: RegularizationConfig):
        self.config = config

    def l2_penalty(self, params: Dict[str, float]) -> float:
        return float(self.config.l2_lambda * sum(v * v for v in params.values()))

    def weight_decay_penalty(self, params: Dict[str, float]) -> float:
        prior = self.config.prior_params
        if prior is None:
            return 0.0
        penalty = 0.0
        for k in params:
            if k in prior:
                diff = params[k] - prior[k]
                penalty += diff * diff
        return float(self.config.weight_decay_lambda * penalty)

    def consistency_penalty(self, params_list: List[Dict[str, float]]) -> float:
        if len(params_list) < 2:
            return 0.0
        penalty = 0.0
        count = 0
        for i in range(len(params_list)):
            for j in range(i + 1, len(params_list)):
                for k in params_list[i]:
                    if k in params_list[j]:
                        diff = params_list[i][k] - params_list[j][k]
                        penalty += diff * diff
                        count += 1
        return float(self.config.consistency_lambda * penalty / max(1, count))

    def compute_total(
        self,
        params: Dict[str, float],
        adapted_params_list: Optional[List[Dict[str, float]]] = None,
    ) -> float:
        total = self.l2_penalty(params)
        total += self.weight_decay_penalty(params)
        if adapted_params_list:
            total += self.consistency_penalty(adapted_params_list)
        return total
