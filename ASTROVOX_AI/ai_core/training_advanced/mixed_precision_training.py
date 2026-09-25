from typing import Optional, Dict, Any
import torch
import torch.nn as nn
import torch.cuda.amp as amp


class MixedPrecisionTraining:
    def __init__(self, enabled: bool = True, dtype: torch.dtype = torch.float16, init_scale: float = 65536.0):
        self.enabled = enabled
        self.dtype = dtype
        self.scaler = amp.GradScaler(enabled=enabled, init_scale=init_scale) if enabled else None
        self.autocast = amp.autocast(enabled=enabled, dtype=dtype) if enabled else amp.autocast(enabled=False)

    def forward(self, model: nn.Module, inputs: torch.Tensor) -> torch.Tensor:
        with self.autocast:
            return model(inputs)

    def backward(self, loss: torch.Tensor) -> None:
        if self.scaler:
            self.scaler.scale(loss).backward()
        else:
            loss.backward()

    def step(self, optimizer: torch.optim.Optimizer) -> None:
        if self.scaler:
            self.scaler.step(optimizer)
            self.scaler.update()
        else:
            optimizer.step()

    def state_dict(self) -> Optional[Dict[str, Any]]:
        return self.scaler.state_dict() if self.scaler else None

    def load_state_dict(self, state_dict: Optional[Dict[str, Any]]) -> None:
        if self.scaler and state_dict:
            self.scaler.load_state_dict(state_dict)
