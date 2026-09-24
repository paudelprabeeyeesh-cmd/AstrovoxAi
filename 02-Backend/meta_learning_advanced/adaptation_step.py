import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class AdaptationStep:
    step_idx: int
    before_params: Dict[str, np.ndarray]
    after_params: Dict[str, np.ndarray]
    loss: float
    grad_norm: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdaptationTracker:
    def __init__(self):
        self.steps: List[AdaptationStep] = []

    def record_step(self, step_idx: int, before_params: Dict[str, np.ndarray], after_params: Dict[str, np.ndarray], loss: float, grad_norm: float, **metadata) -> None:
        step = AdaptationStep(
            step_idx=step_idx,
            before_params={k: np.array(v) for k, v in before_params.items()},
            after_params={k: np.array(v) for k, v in after_params.items()},
            loss=float(loss),
            grad_norm=float(grad_norm),
            metadata=dict(metadata),
        )
        self.steps.append(step)

    def get_trajectory(self) -> List[Dict[str, Any]]:
        return [
            {
                'step_idx': s.step_idx,
                'loss': s.loss,
                'grad_norm': s.grad_norm,
                'param_change': {k: float(np.mean((s.after_params[k] - s.before_params[k]) ** 2)) for k in s.before_params},
                'metadata': s.metadata,
            }
            for s in self.steps
        ]

    def get_summary(self) -> Dict[str, Any]:
        if not self.steps:
            return {'num_steps': 0}
        losses = [s.loss for s in self.steps]
        grad_norms = [s.grad_norm for s in self.steps]
        return {
            'num_steps': len(self.steps),
            'initial_loss': losses[0],
            'final_loss': losses[-1],
            'loss_reduction': losses[0] - losses[-1],
            'mean_grad_norm': float(np.mean(grad_norms)),
            'max_grad_norm': float(np.max(grad_norms)),
        }

    def clear(self) -> None:
        self.steps.clear()
