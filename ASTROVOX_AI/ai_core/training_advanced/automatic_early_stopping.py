from typing import Optional, Dict, Any, List, Callable
import math


class AutomaticEarlyStopping:
    def __init__(self, patience: int = 5, min_delta: float = 0.0, mode: str = 'min', restore_best_weights: bool = True):
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.restore_best_weights = restore_best_weights
        self.best_score: Optional[float] = None
        self.counter = 0
        self.best_weights: Optional[Dict[str, torch.Tensor]] = None
        self.early_stop = False
        self.improved = False

    def __call__(self, score: float, model: Optional[nn.Module] = None) -> bool:
        self.improved = False
        if self.best_score is None:
            self.best_score = score
            self.counter = 0
            self.improved = True
            if self.restore_best_weights and model is not None:
                self.best_weights = {k: v.clone() for k, v in model.state_dict().items()}
            return False
        if self.mode == 'min':
            improved = score < (self.best_score - self.min_delta)
        else:
            improved = score > (self.best_score + self.min_delta)
        if improved:
            self.best_score = score
            self.counter = 0
            self.improved = True
            if self.restore_best_weights and model is not None:
                self.best_weights = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            self.counter += 1
        if self.counter >= self.patience:
            self.early_stop = True
            if self.restore_best_weights and self.best_weights and model is not None:
                model.load_state_dict(self.best_weights)
            return True
        return False

    def reset(self) -> None:
        self.best_score = None
        self.counter = 0
        self.best_weights = None
        self.early_stop = False
