from typing import Any, Dict, List, Optional


class AdaptationStep:
    def __init__(
        self,
        step_idx: int,
        before_params: Dict[str, float],
        after_params: Dict[str, float],
        loss: float,
        grad_norm: float,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ):
        self.step_idx = step_idx
        self.before_params = dict(before_params)
        self.after_params = dict(after_params)
        self.loss = float(loss)
        self.grad_norm = float(grad_norm)
        self.metadata = dict(metadata) if metadata is not None else {}
        self.metadata.update(kwargs)


class AdaptationTracker:
    def __init__(self):
        self.steps: List[AdaptationStep] = []

    def record_step(
        self,
        step_idx: int,
        before_params: Dict[str, float],
        after_params: Dict[str, float],
        loss: float,
        grad_norm: float,
        **metadata: Any,
    ) -> None:
        step = AdaptationStep(
            step_idx=step_idx,
            before_params=dict(before_params),
            after_params=dict(after_params),
            loss=float(loss),
            grad_norm=float(grad_norm),
            metadata=dict(metadata),
        )
        self.steps.append(step)

    def get_trajectory(self) -> List[Dict[str, Any]]:
        return [
            {
                "step_idx": s.step_idx,
                "loss": s.loss,
                "grad_norm": s.grad_norm,
                "param_change": {
                    k: (s.after_params[k] - s.before_params[k]) ** 2
                    for k in s.before_params
                },
                "metadata": s.metadata,
            }
            for s in self.steps
        ]

    def get_summary(self) -> Dict[str, Any]:
        if not self.steps:
            return {"num_steps": 0}
        losses = [s.loss for s in self.steps]
        grad_norms = [s.grad_norm for s in self.steps]
        return {
            "num_steps": len(self.steps),
            "initial_loss": losses[0],
            "final_loss": losses[-1],
            "loss_reduction": losses[0] - losses[-1],
            "mean_grad_norm": sum(grad_norms) / len(grad_norms),
            "max_grad_norm": max(grad_norms),
        }

    def clear(self) -> None:
        self.steps.clear()
