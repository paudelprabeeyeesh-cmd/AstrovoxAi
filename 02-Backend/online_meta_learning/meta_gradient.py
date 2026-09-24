import numpy as np
from typing import Dict, List, Optional, Tuple, Any


class MetaGradientComputer:
    def __init__(self, normalize: bool = True, clip_norm: Optional[float] = 1.0):
        self.normalize = normalize
        self.clip_norm = clip_norm
        self.gradient_history: List[Dict[str, np.ndarray]] = []

    def compute(
        self,
        adapted_params: Dict[str, np.ndarray],
        base_params: Dict[str, np.ndarray],
        query_loss_grad: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        meta_grad: Dict[str, np.ndarray] = {}
        for k in base_params:
            if k not in adapted_params:
                continue
            diff = adapted_params[k] - base_params[k]
            if k in query_loss_grad:
                meta_grad[k] = diff * query_loss_grad[k]
            else:
                meta_grad[k] = diff
        if self.normalize:
            meta_grad = self._normalize(meta_grad)
        if self.clip_norm is not None:
            meta_grad = self._clip(meta_grad)
        self.gradient_history.append(meta_grad)
        return meta_grad

    def _normalize(self, grads: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        total = sum(np.sum(v ** 2) for v in grads.values())
        if total <= 0:
            return grads
        scale = 1.0 / np.sqrt(total)
        return {k: v * scale for k, v in grads.items()}

    def _clip(self, grads: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        result: Dict[str, np.ndarray] = {}
        for k, v in grads.items():
            norm = np.sqrt(np.sum(v ** 2))
            if norm > self.clip_norm:
                v = v * (self.clip_norm / norm)
            result[k] = v
        return result

    def average_history(self) -> Dict[str, np.ndarray]:
        if not self.gradient_history:
            return {}
        keys = self.gradient_history[0].keys()
        avg: Dict[str, np.ndarray] = {}
        for k in keys:
            stack = np.stack([g[k] for g in self.gradient_history])
            avg[k] = np.mean(stack, axis=0)
        return avg

    def get_report(self) -> Dict[str, Any]:
        return {
            'num_gradients': len(self.gradient_history),
            'last_keys': list(self.gradient_history[-1].keys()) if self.gradient_history else [],
            'normalize': self.normalize,
            'clip_norm': self.clip_norm,
        }
