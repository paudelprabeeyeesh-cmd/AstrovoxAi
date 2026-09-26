from typing import List, Dict, Any
import torch
import torch.nn as nn


class CheckpointMerger:
    @staticmethod
    def merge_models(models: List[nn.Module], weights: Optional[List[float]] = None, method: str = 'linear') -> nn.Module:
        if weights is None:
            weights = [1.0 / len(models)] * len(models)
        base_model = models[0]
        base_state_dict = base_model.state_dict()
        merged_state_dict = {key: torch.zeros_like(param) for key, param in base_state_dict.items()}
        for model, weight in zip(models, weights):
            state_dict = model.state_dict()
            for key in merged_state_dict:
                if key in state_dict:
                    merged_state_dict[key] += weight * state_dict[key]
        base_model.load_state_dict(merged_state_dict)
        return base_model

    @staticmethod
    def slerp(model_a: nn.Module, model_b: nn.Module, t: float = 0.5) -> nn.Module:
        state_dict_a = model_a.state_dict()
        state_dict_b = model_b.state_dict()
        result = {}
        for key in state_dict_a:
            if key in state_dict_b:
                vec_a = state_dict_a[key].float().flatten()
                vec_b = state_dict_b[key].float().flatten()
                norm_a = vec_a.norm()
                norm_b = vec_b.norm()
                if norm_a == 0 or norm_b == 0:
                    result[key] = (1 - t) * state_dict_a[key] + t * state_dict_b[key]
                else:
                    omega = torch.acos(torch.dot(vec_a / norm_a, vec_b / norm_b).clamp(-1, 1))
                    sin_omega = torch.sin(omega)
                    result[key] = (torch.sin((1 - t) * omega) / sin_omega) * state_dict_a[key] + (torch.sin(t * omega) / sin_omega) * state_dict_b[key]
            else:
                result[key] = state_dict_a[key]
        model_a.load_state_dict(result)
        return model_a
